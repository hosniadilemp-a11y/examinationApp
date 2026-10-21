from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Module, User
from backend.app.schemas import (
    ModuleCreate, ModuleUpdate, ModuleResponse, 
    UserResponse, UserBrief, TeacherModuleAssign
)
from backend.app.dependencies import require_admin, require_teacher_or_admin

router = APIRouter(prefix="/api/modules", tags=["Gestion des Modules"])

@router.get("", response_model=List[ModuleResponse])
def list_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste tous les modules de cours disponibles."""
    modules = db.query(Module).all()
    results = []
    for m in modules:
        results.append(ModuleResponse(
            code=m.code,
            title=m.title,
            description=m.description,
            created_at=m.created_at,
            teachers=[
                UserBrief(id=t.id, username=t.username, full_name=t.full_name, role=t.role)
                for t in (m.teachers or [])
            ]
        ))
    return results

@router.post("", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
def create_module(
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Crée un nouveau module académique (réservé aux administrateurs)."""
    code_clean = payload.code.strip().upper()
    existing = db.query(Module).filter(Module.code == code_clean).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Un module avec le code '{code_clean}' existe déjà."
        )
    
    module = Module(
        code=code_clean,
        title=payload.title.strip(),
        description=payload.description
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return ModuleResponse(
        code=module.code,
        title=module.title,
        description=module.description,
        created_at=module.created_at,
        teachers=[]
    )

@router.get("/{module_code}", response_model=ModuleResponse)
def get_module(
    module_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Récupère les détails d'un module spécifique."""
    module = db.query(Module).filter(Module.code == module_code.upper()).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
    return ModuleResponse(
        code=module.code,
        title=module.title,
        description=module.description,
        created_at=module.created_at,
        teachers=[
            UserBrief(id=t.id, username=t.username, full_name=t.full_name, role=t.role)
            for t in (module.teachers or [])
        ]
    )

@router.get("/{module_code}/teachers", response_model=List[UserResponse])
def get_module_teachers(
    module_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste les enseignants affectés à un module donné."""
    module = db.query(Module).filter(Module.code == module_code.upper()).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
    return module.teachers

@router.post("/{module_code}/teachers", status_code=status.HTTP_200_OK)
def assign_teacher_to_module(
    module_code: str,
    payload: TeacherModuleAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Affecte un enseignant à un module spécifique (réservé aux administrateurs)."""
    module = db.query(Module).filter(Module.code == module_code.upper()).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
    
    teacher = db.query(User).filter(User.id == payload.teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enseignant introuvable.")
        
    if teacher not in module.teachers:
        module.teachers.append(teacher)
        db.commit()
        
    return {"success": True, "message": f"Enseignant {teacher.full_name} affecté au module {module.code}."}

@router.delete("/{module_code}/teachers/{teacher_id}", status_code=status.HTTP_200_OK)
def remove_teacher_from_module(
    module_code: str,
    teacher_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Retire un enseignant d'un module (réservé aux administrateurs)."""
    module = db.query(Module).filter(Module.code == module_code.upper()).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
    
    teacher = db.query(User).filter(User.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enseignant introuvable.")
        
    if teacher in module.teachers:
        module.teachers.remove(teacher)
        db.commit()
        
    return {"success": True, "message": f"Enseignant {teacher.full_name} retiré du module {module.code}."}

@router.put("/{module_code}", response_model=ModuleResponse)
def update_module(
    module_code: str,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Met à jour les informations d'un module (réservé aux administrateurs)."""
    module = db.query(Module).filter(Module.code == module_code.upper()).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
        
    if payload.title is not None:
        module.title = payload.title.strip()
    if payload.description is not None:
        module.description = payload.description
        
    db.commit()
    db.refresh(module)
    return module

@router.delete("/{module_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Supprime un module (réservé aux administrateurs)."""
    module = db.query(Module).filter(Module.code == module_code.upper()).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
        
    db.delete(module)
    db.commit()
    return None
