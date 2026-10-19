from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, Group
from backend.app.schemas import UserCreate, UserUpdate, UserResponse
from backend.app.security import hash_password
from backend.app.dependencies import require_admin, require_teacher_or_admin

router = APIRouter(prefix="/api/users", tags=["Gestion des Utilisateurs"])

@router.get("", response_model=List[UserResponse])
def list_users(
    role: Optional[str] = Query(None, pattern="^(admin|teacher|student)$"),
    group_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste les utilisateurs filtrés par rôle ou par groupe."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if group_id:
        query = query.filter(User.group_id == group_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
        
    users = query.offset(skip).limit(limit).all()
    return users

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Crée un nouvel utilisateur (réservé aux administrateurs)."""
    username_clean = payload.username.strip()
    existing = db.query(User).filter(User.username == username_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un utilisateur avec l'identifiant '{username_clean}' existe déjà."
        )
        
    user_id = payload.id.strip() if payload.id else username_clean
    existing_id = db.query(User).filter(User.id == user_id).first()
    if existing_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un utilisateur avec l'ID '{user_id}' existe déjà."
        )
        
    if payload.group_id:
        group = db.query(Group).filter(Group.id == payload.group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le groupe '{payload.group_id}' n'existe pas."
            )
            
    # Détermination du mot de passe initial
    # Pour un étudiant, si aucun mot de passe n'est fourni, mot de passe initial = user_id
    plain_password = payload.password if payload.password else user_id
    
    new_user = User(
        id=user_id,
        username=username_clean,
        password_hash=hash_password(plain_password),
        plain_password=plain_password,
        full_name=payload.full_name.strip(),
        email=payload.email.strip() if payload.email else None,
        role=payload.role,
        group_id=payload.group_id,
        must_change_password=payload.must_change_password if payload.must_change_password is not None else True,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Récupère les détails d'un utilisateur par son ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Met à jour un utilisateur (réservé aux administrateurs)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
        
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.email is not None:
        user.email = payload.email.strip() if payload.email else None
    if payload.role is not None:
        user.role = payload.role
    if payload.group_id is not None:
        if payload.group_id:
            group = db.query(Group).filter(Group.id == payload.group_id).first()
            if not group:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Groupe inexistant.")
        user.group_id = payload.group_id if payload.group_id else None
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None and payload.password.strip():
        pwd_clean = payload.password.strip()
        user.password_hash = hash_password(pwd_clean)
        user.plain_password = pwd_clean
        
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Supprime un utilisateur (réservé aux administrateurs)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de supprimer votre propre compte administrateur."
        )
        
    db.delete(user)
    db.commit()
    return None
