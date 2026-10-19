from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Group, User
from backend.app.schemas import GroupCreate, GroupUpdate, GroupResponse, UserResponse
from backend.app.dependencies import get_current_user, require_admin, require_teacher_or_admin

router = APIRouter(prefix="/api/groups", tags=["Gestion des Groupes"])

@router.get("", response_model=List[GroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste tous les groupes académiques avec le nombre d'étudiants rattachés."""
    groups = db.query(Group).all()
    results = []
    for g in groups:
        count = db.query(User).filter(User.group_id == g.id).count()
        resp = GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            created_at=g.created_at,
            student_count=count
        )
        results.append(resp)
    return results

@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Crée un nouveau groupe académique (réservé aux administrateurs)."""
    existing = db.query(Group).filter(Group.id == payload.id.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un groupe avec l'identifiant '{payload.id}' existe déjà."
        )
    
    group = Group(
        id=payload.id.strip(),
        name=payload.name.strip(),
        description=payload.description
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        student_count=0
    )

@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Récupère les détails d'un groupe spécifique."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Groupe '{group_id}' introuvable."
        )
    
    count = db.query(User).filter(User.group_id == group.id).count()
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        student_count=count
    )

@router.get("/{group_id}/students", response_model=List[UserResponse])
def get_group_students(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste tous les étudiants appartenant à un groupe donné."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable.")
    
    students = db.query(User).filter(User.group_id == group_id, User.role == "student").all()
    return students

@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Met à jour les informations d'un groupe (réservé aux administrateurs)."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable.")
    
    if payload.name is not None:
        group.name = payload.name.strip()
    if payload.description is not None:
        group.description = payload.description
        
    db.commit()
    db.refresh(group)
    
    count = db.query(User).filter(User.group_id == group.id).count()
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        student_count=count
    )

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Supprime un groupe (réservé aux administrateurs)."""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Groupe introuvable.")
    
    db.delete(group)
    db.commit()
    return None
