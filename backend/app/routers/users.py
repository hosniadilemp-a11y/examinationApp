import re
import uuid
import unicodedata
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, Group
from backend.app.schemas import UserCreate, UserUpdate, UserResponse
from backend.app.security import hash_password
from backend.app.dependencies import require_admin, require_teacher_or_admin

router = APIRouter(prefix="/api/users", tags=["Gestion des Utilisateurs"])


def _slugify_login(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", norm.lower()).strip(".")
    return cleaned or "user"


def generate_unique_credentials(db: Session, full_name: str, role: str, user_id: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
    prefix_id = "TCH" if role == "teacher" else ("ADM" if role == "admin" else "ETU")
    prefix_login = "prof_" if role == "teacher" else ("admin_" if role == "admin" else "etu_")
    prefix_pwd = "Prof" if role == "teacher" else ("Admin" if role == "admin" else "Etu")

    final_id = (user_id or "").strip()
    if not final_id:
        idx = db.query(User).filter(User.role == role).count() + 1
        final_id = f"{prefix_id}-{idx:03d}"
        while db.query(User).filter(User.id == final_id).first():
            idx += 1
            final_id = f"{prefix_id}-{idx:03d}"

    final_username = (username or "").strip()
    if not final_username:
        slug = _slugify_login(full_name).replace(".", "_")
        base_u = f"{prefix_login}{slug}"[:28]
        final_username = base_u
        counter = 1
        while db.query(User).filter(User.username == final_username).first():
            counter += 1
            final_username = f"{base_u}{counter}"

    final_pwd = (password or "").strip()
    if not final_pwd:
        suffix = re.sub(r"[^a-zA-Z0-9]", "", final_id)[-4:] or "2026"
        final_pwd = f"{prefix_pwd}@{suffix}!"

    return final_id, final_username, final_pwd


@router.get("", response_model=List[UserResponse])
def list_users(
    role: Optional[str] = Query(None, pattern="^(admin|teacher|student)$"),
    group_id: Optional[str] = None,
    enrollment_year: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste les utilisateurs filtrés par rôle, groupe ou année d'inscription."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if group_id:
        query = query.filter(User.group_id == group_id)
    if enrollment_year:
        query = query.filter(User.enrollment_year == enrollment_year)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
        
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/enrollment-years", response_model=List[str])
def list_enrollment_years(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Retourne la liste ordonnée et distincte des promotions/années d'inscription."""
    rows = db.query(User.enrollment_year).filter(
        User.enrollment_year.isnot(None),
        User.enrollment_year != ""
    ).distinct().all()
    years = [r[0] for r in rows if r[0]]
    return sorted(years, reverse=True)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Crée un nouvel utilisateur (génère automatiquement login et mot de passe si omis)."""
    if payload.username and payload.username.strip():
        existing = db.query(User).filter(User.username == payload.username.strip()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Un utilisateur avec l'identifiant '{payload.username.strip()}' existe déjà."
            )

    if payload.id and payload.id.strip():
        existing_id = db.query(User).filter(User.id == payload.id.strip()).first()
        if existing_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Un utilisateur avec l'ID '{payload.id.strip()}' existe déjà."
            )

    user_id, username_clean, plain_password = generate_unique_credentials(
        db=db,
        full_name=payload.full_name,
        role=payload.role,
        user_id=payload.id or (payload.username if payload.username else None),
        username=payload.username,
        password=payload.password
    )

    if payload.group_id:
        group = db.query(Group).filter(Group.id == payload.group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le groupe '{payload.group_id}' n'existe pas."
            )

    new_user = User(
        id=user_id,
        username=username_clean,
        password_hash=hash_password(plain_password),
        plain_password=plain_password,
        full_name=payload.full_name.strip(),
        email=payload.email.strip() if payload.email else None,
        role=payload.role,
        group_id=payload.group_id,
        enrollment_year=payload.enrollment_year.strip() if payload.enrollment_year else "2025-2026",
        must_change_password=payload.must_change_password if payload.must_change_password is not None else False,
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
    """Met à jour un utilisateur (y compris son identifiant login et son mot de passe)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    if payload.username is not None and payload.username.strip():
        new_uname = payload.username.strip()
        if new_uname != user.username:
            conflict = db.query(User).filter(User.username == new_uname, User.id != user.id).first()
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"L'identifiant '{new_uname}' est déjà utilisé par un autre compte."
                )
            user.username = new_uname

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
    if payload.enrollment_year is not None:
        user.enrollment_year = payload.enrollment_year.strip() if payload.enrollment_year else None
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
