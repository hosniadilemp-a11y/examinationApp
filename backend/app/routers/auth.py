from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, AuditLog
from backend.app.schemas import (
    LoginRequest, Token, UserResponse, 
    PasswordChangeRequest, PasswordResetRequest
)
from backend.app.security import (
    verify_password, hash_password, create_access_token
)
from backend.app.dependencies import get_current_user, require_teacher_or_admin

router = APIRouter(prefix="/api/auth", tags=["Authentification"])

@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authentifie un utilisateur (Admin, Enseignant ou Étudiant) avec son nom d'utilisateur et mot de passe."""
    user = db.query(User).filter(User.username == login_data.username.strip()).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Votre compte a été désactivé par l'administrateur."
        )
    
    # Création du jeton JWT
    access_token = create_access_token(
        data={
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "must_change_password": user.must_change_password
        }
    )
    
    # Enregistrement dans le journal d'audit
    log_entry = AuditLog(
        student_id=user.id if user.role == "student" else None,
        event_type="LOGIN",
        details_json=f'{{"role": "{user.role}", "username": "{user.username}"}}'
    )
    db.add(log_entry)
    db.commit()
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        must_change_password=user.must_change_password
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Récupère le profil de l'utilisateur actuellement connecté."""
    return current_user

@router.post("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permet à l'utilisateur de modifier son mot de passe (obligatoire lors de la première connexion)."""
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'ancien mot de passe fourni est incorrect."
        )
    
    if payload.new_password == payload.old_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit être différent de l'ancien."
        )
        
    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    
    # Audit log
    db.add(AuditLog(
        student_id=current_user.id if current_user.role == "student" else None,
        event_type="PASSWORD_CHANGED",
        details_json=f'{{"username": "{current_user.username}"}}'
    ))
    db.commit()
    
    return {
        "success": True,
        "message": "Mot de passe modifié avec succès. Votre compte est désormais pleinement activé."
    }

@router.post("/reset-password")
def reset_password(
    payload: PasswordResetRequest,
    current_user: User = Depends(require_teacher_or_admin),
    db: Session = Depends(get_db)
):
    """Permet à un Enseignant ou Administrateur de réinitialiser le mot de passe d'un étudiant."""
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable."
        )
    
    # Si l'appelant est enseignant, il ne peut réinitialiser que des étudiants
    if current_user.role == "teacher" and target_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Un enseignant ne peut réinitialiser que les mots de passe des étudiants."
        )
    
    # Réinitialisation par défaut avec l'identifiant (target_user.id)
    new_plain_pass = payload.new_password if payload.new_password else target_user.id
    target_user.password_hash = hash_password(new_plain_pass)
    target_user.must_change_password = True
    
    db.add(AuditLog(
        student_id=target_user.id if target_user.role == "student" else None,
        event_type="PASSWORD_RESET",
        details_json=f'{{"reset_by": "{current_user.username}", "target": "{target_user.username}"}}'
    ))
    db.commit()
    
    return {
        "success": True,
        "message": f"Mot de passe de l'utilisateur {target_user.username} réinitialisé avec succès.",
        "must_change_password": True
    }
