from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User
from backend.app.dependencies import get_current_user
from backend.app.services.linux_training_service import (
    load_linux_curriculum,
    load_linux_challenges,
    get_levels_summary,
    get_safe_challenges_list,
    get_challenge_detail_student,
    get_theory_quizzes,
    evaluate_linux_challenge,
    sync_student_linux_pillar,
    get_student_linux_progress,
    get_student_linux_history,
    list_linux_chapters,
    get_linux_chapter_details,
    generate_linux_session,
    evaluate_linux_session_submission,
    get_linux_progression_stats
)

router = APIRouter(prefix="/api/training/linux", tags=["Centre d'Entraînement Linux"])

# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class LinuxSessionRequest(BaseModel):
    chapter_id: Optional[str] = None
    level: Optional[int] = None
    assessment_type: str = "all"  # 'all' | 'theoretical' | 'practical'
    count: int = 10

class LinuxChallengeSubmitRequest(BaseModel):
    challenge_id: str
    command: str
    vfs_state: Optional[Dict[str, Any]] = None
    execution_output: Optional[Dict[str, Any]] = None
    client_tests_passed: Optional[bool] = None

class LinuxAnswerItem(BaseModel):
    id: Any
    type: Optional[str] = "single_choice"
    topic: Optional[str] = "Linux"
    student_answer: Any = None
    is_correct: Optional[Any] = None
    vfs_state: Optional[Dict[str, Any]] = None
    execution_output: Optional[Dict[str, Any]] = None

class LinuxSubmitSessionRequest(BaseModel):
    answers: List[LinuxAnswerItem]

# ==============================================================================
# Curriculum & Challenges Endpoints
# ==============================================================================

@router.get("/curriculum")
def get_curriculum(
    current_user: User = Depends(get_current_user)
):
    """Retourne la structure complète du cursus Linux avec les 4 niveaux et objectifs."""
    levels = get_levels_summary()
    return {
        "curriculum_title": "Cursus d'Entraînement Linux & Administration Système",
        "total_levels": len(levels),
        "levels": levels
    }

@router.get("/challenges")
def get_challenges(
    level: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retourne la liste des défis pratiques (filtrable par niveau 1-4).
    Exclut strictement les champs confidentiels (hidden_tests et solution).
    """
    return get_safe_challenges_list(level=level, user_id=current_user.id, db=db)

@router.get("/challenges/{challenge_id}")
def get_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retourne le détail d'un défi pratique pour l'espace de travail étudiant.
    Masque rigoureusement les tests cachés et solutions.
    """
    details = get_challenge_detail_student(challenge_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Défi Linux '{challenge_id}' introuvable."
        )
    return details

@router.get("/theory/quizzes")
def get_quizzes(
    level: Optional[int] = None,
    topic: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Retourne les questions théoriques (FHS, signaux, permissions) avec réponses masquées.
    """
    return get_theory_quizzes(level=level, topic=topic)

# ==============================================================================
# Training Session Generation & Submissions
# ==============================================================================

@router.post("/generate-session")
def generate_session(
    payload: LinuxSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """Génère une session d'entraînement dynamique filtrée par chapitre, niveau ou type."""
    return generate_linux_session(
        chapter_id=payload.chapter_id,
        assessment_type=payload.assessment_type,
        count=payload.count,
        target_level=payload.level
    )

@router.post("/submit-challenge")
def submit_challenge(
    payload: LinuxChallengeSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Évalue la soumission d'un défi pratique Linux (commande + VFS).
    Vérifie les tests publics et cachés (les détails des tests cachés restent protégés).
    Synchronise avec le pilier diagnostique LINUX_ADMIN (découplage strict des examens officiels).
    """
    eval_result = evaluate_linux_challenge(
        challenge_id=payload.challenge_id,
        command=payload.command,
        vfs_state=payload.vfs_state,
        execution_output=payload.execution_output,
        client_tests_passed=payload.client_tests_passed
    )

    # Synchronisation avec le pilier LINUX_ADMIN
    sync_student_linux_pillar(
        user_id=current_user.id,
        score=eval_result["awarded_points"],
        db=db,
        answers={"challenge_id": payload.challenge_id, "command": payload.command},
        details=[eval_result],
        max_score=eval_result["max_points"] or 20.0
    )

    return eval_result

@router.post("/submit-session")
def submit_session(
    payload: LinuxSubmitSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Évalue une session d'entraînement complète (QCM et commandes pratiques).
    Calcule la note sur 20 et persiste la tentative dans PracticeAttempt.
    """
    answers_dict = [item.model_dump() for item in payload.answers]
    result = evaluate_linux_session_submission(db, current_user, answers_dict)
    return result

# ==============================================================================
# Progress & History Endpoints
# ==============================================================================

@router.get("/progress")
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne la progression globale de l'étudiant sur le cursus Linux."""
    return get_student_linux_progress(current_user.id, db)

@router.get("/progression")
def get_progression(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Alias pour la compatibilité avec l'interface existante."""
    return get_student_linux_progress(current_user.id, db)

@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne l'historique complet des tentatives de l'étudiant dans le Centre Linux."""
    return get_student_linux_history(current_user.id, db)

# ==============================================================================
# Chapter-based Legacy Endpoints (for existing UI / tests compatibility)
# ==============================================================================

@router.get("/chapters")
def get_chapters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retourne la liste des chapitres avec l'avancement de l'étudiant."""
    return list_linux_chapters(db, current_user.id)

@router.get("/chapters/{chapter_id}")
def get_chapter(
    chapter_id: str,
    assessment_type: str = "all",
    current_user: User = Depends(get_current_user)
):
    """Retourne le contenu complet d'un chapitre (exercices théoriques et pratiques)."""
    details = get_linux_chapter_details(chapter_id, assessment_type)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapitre Linux '{chapter_id}' introuvable."
        )
    return details
