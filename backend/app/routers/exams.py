import uuid
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Exam, Question, Module, Group, User, ExamSession
from backend.app.schemas import (
    ExamCreate, ExamUpdate, ExamResponse, ExamDetailResponse,
    QuestionCreate, QuestionUpdate, QuestionResponse,
    QuestionOrderItem, QuestionReorderPayload
)
from backend.app.dependencies import get_current_user, require_teacher_or_admin
from backend.app.services.item_analysis import calculate_exam_item_analysis, generate_item_analysis_csv
from backend.app.routers.proctor import auto_close_all_expired_sessions

router = APIRouter(prefix="/api/exams", tags=["Gestion des Examens & Questions"])

def _check_module_permission(user: User, module_code: str):
    """Vérifie que l'enseignant est bien affecté au module ou est administrateur."""
    if user.role == "admin":
        return True
    assigned = [m.code for m in user.assigned_modules]
    if module_code.upper() not in assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Vous n'êtes pas affecté au module '{module_code}'. Action non autorisée."
        )
    return True

@router.get("", response_model=List[ExamResponse])
def list_exams(
    module_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Liste les examens créés (filtrable par module)."""
    auto_close_all_expired_sessions(db)
    query = db.query(Exam)
    if module_code:
        query = query.filter(Exam.module_code == module_code.upper())
        
    # Si l'utilisateur est étudiant, il ne voit que les examens assignés à son groupe
    if current_user.role == "student":
        if current_user.group_id:
            query = query.filter(Exam.groups.any(id=current_user.group_id))
        else:
            return []
    # Si l'utilisateur est enseignant, il ne voit QUE les examens de ses modules assignés
    elif current_user.role == "teacher":
        assigned_codes = [m.code.upper() for m in current_user.assigned_modules]
        if assigned_codes:
            query = query.filter(Exam.module_code.in_(assigned_codes))
        else:
            return []
            
    exams = query.all()
    results = []
    for e in exams:
        count = len(e.questions)
        group_ids = [g.id for g in e.groups]
        tot_pts = round(sum(q.points for q in e.questions), 2)

        # Déterminer l'état de session de l'examen (not_started | waiting | in_progress | completed)
        sess_status = "not_started"
        active_sess_id = None
        sub_count = 0
        if e.sessions:
            # Trier les sessions : priorité à in_progress > waiting > completed
            for s in e.sessions:
                sub_count += sum(1 for att in s.attempts if att.status in ["submitted", "timed_out", "completed"])
            in_prog = next((s for s in e.sessions if s.status == "in_progress"), None)
            waiting_s = next((s for s in e.sessions if s.status == "waiting"), None)
            comp_s = next((s for s in e.sessions if s.status in ["completed", "closed", "finished"]), None)
            if in_prog:
                sess_status = "in_progress"
                active_sess_id = in_prog.id
            elif waiting_s:
                sess_status = "waiting"
                active_sess_id = waiting_s.id
            elif comp_s:
                sess_status = "completed"
                active_sess_id = comp_s.id

        resp = ExamResponse(
            id=e.id,
            module_code=e.module_code,
            title=e.title,
            exam_type=getattr(e, "exam_type", "theoretical") or "theoretical",
            instructions=e.instructions,
            duration_minutes=e.duration_minutes,
            global_points=e.global_points,
            total_question_points=tot_pts,
            passing_score=getattr(e, "passing_score", 10.0) or 10.0,
            navigation_mode=e.navigation_mode,
            shuffle_questions=e.shuffle_questions,
            shuffle_options=e.shuffle_options,
            partial_credit_enabled=e.partial_credit_enabled,
            default_negative_penalty=e.default_negative_penalty,
            created_by=e.created_by,
            created_at=e.created_at,
            question_count=count,
            assigned_groups=group_ids,
            session_status=sess_status,
            active_session_id=active_sess_id,
            submitted_count=sub_count
        )
        results.append(resp)
    return results

@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Crée un nouvel examen rattaché à un module spécifique."""
    module_code_clean = payload.module_code.strip().upper()
    module = db.query(Module).filter(Module.code == module_code_clean).first()
    if not module:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module introuvable.")
        
    _check_module_permission(current_user, module_code_clean)

    exam_type_val = payload.exam_type or "theoretical"

    # Règle de plateforme : Pour les modules hors Python, seul le mode 'theoretical' est autorisé
    is_python_module = "PYTHON" in module_code_clean
    if exam_type_val == "practical" and not is_python_module:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pour le moment, seules les épreuves de type 'Théorique' sont autorisées pour ce module. Le mode pratique est réservé exclusivement au module Python."
        )
    # Validation des questions embarquées si fournies dans payload
    if payload.questions:
        for q_item in payload.questions:
            if exam_type_val == "theoretical" and q_item.type in ["coding", "code"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Une épreuve théorique ne peut pas contenir de défi de programmation Python. Choisissez une épreuve pratique."
                )
            if exam_type_val == "practical" and q_item.type not in ["coding", "code"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Une épreuve pratique doit contenir exclusivement des défis de programmation Python."
                )
    
    exam_id = f"EXAM-{uuid.uuid4().hex[:8].upper()}"
    new_exam = Exam(
        id=exam_id,
        module_code=module_code_clean,
        title=payload.title.strip(),
        exam_type=exam_type_val,
        instructions=payload.instructions,
        duration_minutes=payload.duration_minutes,
        global_points=payload.global_points,
        navigation_mode=payload.navigation_mode,
        shuffle_questions=payload.shuffle_questions,
        shuffle_options=payload.shuffle_options,
        partial_credit_enabled=payload.partial_credit_enabled,
        default_negative_penalty=payload.default_negative_penalty,
        created_by=current_user.id
    )
    
    if payload.group_ids:
        groups = db.query(Group).filter(Group.id.in_(payload.group_ids)).all()
        new_exam.groups.extend(groups)
        
    db.add(new_exam)
    db.flush()

    question_count = 0
    # Insertion des questions fournies dans le payload
    if payload.questions:
        for idx, q_data in enumerate(payload.questions, start=1):
            q_id = f"Q-{uuid.uuid4().hex[:8].upper()}"
            new_q = Question(
                id=q_id,
                exam_id=new_exam.id,
                ordering=q_data.ordering or idx,
                type=q_data.type,
                prompt_markdown=q_data.prompt_markdown,
                points=q_data.points,
                negative_penalty=q_data.negative_penalty,
                time_limit_seconds=q_data.time_limit_seconds,
                options_json=q_data.options_json,
                correct_answers_json=q_data.correct_answers_json
            )
            db.add(new_q)
            question_count += 1

    # Si room_id est explicitement fourni (création personnalisée depuis l'interface)
    if payload.room_id:
        room_id = payload.room_id.strip()
        candidate_template = None
        if TEMPLATES_DIR.exists():
            for f in TEMPLATES_DIR.glob("*.json"):
                if module_code_clean.lower() in f.stem.lower() or f.stem.lower() in module_code_clean.lower():
                    candidate_template = f
                    break

        if candidate_template and candidate_template.exists() and not payload.questions:
            try:
                with open(candidate_template, "r", encoding="utf-8") as fp:
                    tdata = json.load(fp)
                for idx, q_data in enumerate(tdata.get("questions", []), start=1):
                    q_type = str(q_data.get("type", "single_choice"))
                    if exam_type_val == "theoretical" and q_type in ["coding", "code"]:
                        continue
                    if exam_type_val == "practical" and q_type not in ["coding", "code"]:
                        continue
                    q_id = f"Q-{uuid.uuid4().hex[:8].upper()}"
                    opts = q_data.get("options_json", "[]")
                    opts_str = json.dumps(opts, ensure_ascii=False) if isinstance(opts, (list, dict)) else str(opts)
                    corr = q_data.get("correct_answers_json", "")
                    corr_str = json.dumps(corr, ensure_ascii=False) if isinstance(corr, (list, dict)) else str(corr)
                    new_q = Question(
                        id=q_id,
                        exam_id=new_exam.id,
                        ordering=int(q_data.get("ordering", idx)),
                        type=q_type,
                        prompt_markdown=str(q_data.get("prompt_markdown", "")),
                        points=float(q_data.get("points", 2.0)),
                        negative_penalty=float(q_data.get("negative_penalty", 0.0)),
                        time_limit_seconds=q_data.get("time_limit_seconds"),
                        options_json=opts_str,
                        correct_answers_json=corr_str
                    )
                    db.add(new_q)
                    question_count += 1
            except Exception as e:
                print(f"[create_exam] Template question copy error: {e}")

        # Créer automatiquement une session de salle en attente pour la salle demandée
        existing_sess = db.query(ExamSession).filter(ExamSession.exam_id == new_exam.id, ExamSession.room_id == room_id).first()
        if not existing_sess:
            sess_id = f"SESS-{uuid.uuid4().hex[:8].upper()}"
            session = ExamSession(
                id=sess_id,
                exam_id=new_exam.id,
                room_id=room_id,
                status="waiting",
                launched_by=current_user.id
            )
            db.add(session)

    db.commit()
    db.refresh(new_exam)
    
    total_pts = round(sum(q.points for q in new_exam.questions), 2)
    return ExamResponse(
        id=new_exam.id,
        module_code=new_exam.module_code,
        title=new_exam.title,
        exam_type=getattr(new_exam, "exam_type", "theoretical") or "theoretical",
        instructions=new_exam.instructions,
        duration_minutes=new_exam.duration_minutes,
        global_points=new_exam.global_points,
        total_question_points=total_pts,
        passing_score=getattr(new_exam, "passing_score", 10.0) or 10.0,
        navigation_mode=new_exam.navigation_mode,
        shuffle_questions=new_exam.shuffle_questions,
        shuffle_options=new_exam.shuffle_options,
        partial_credit_enabled=new_exam.partial_credit_enabled,
        default_negative_penalty=new_exam.default_negative_penalty,
        created_by=new_exam.created_by,
        created_at=new_exam.created_at,
        question_count=len(new_exam.questions),
        assigned_groups=[g.id for g in new_exam.groups]
    )

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "seeds" / "templates"

def _create_exam_from_template_dict(data: dict, db: Session, current_user: User) -> Exam:
    module_code_clean = str(data.get("module_code", "")).strip().upper()
    module = db.query(Module).filter(Module.code == module_code_clean).first()
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_code_clean}' introuvable. Veuillez d'abord créer le module."
        )
    _check_module_permission(current_user, module_code_clean)
    
    exam_id = f"EXAM-{uuid.uuid4().hex[:8].upper()}"
    new_exam = Exam(
        id=exam_id,
        module_code=module_code_clean,
        title=str(data.get("title", f"Examen {module_code_clean}")).strip(),
        exam_type=str(data.get("exam_type", "theoretical")),
        instructions=data.get("instructions", "Épreuve officielle sur poste individuel."),
        duration_minutes=int(data.get("duration_minutes", 45)),
        global_points=float(data.get("global_points", 20.0)),
        navigation_mode=data.get("navigation_mode", "free"),
        shuffle_questions=bool(data.get("shuffle_questions", True)),
        shuffle_options=bool(data.get("shuffle_options", True)),
        partial_credit_enabled=bool(data.get("partial_credit_enabled", True)),
        default_negative_penalty=float(data.get("default_negative_penalty", 0.5)),
        created_by=current_user.id
    )
    
    group_ids = data.get("group_ids", [])
    if group_ids:
        groups = db.query(Group).filter(Group.id.in_(group_ids)).all()
        new_exam.groups.extend(groups)
        
    db.add(new_exam)
    db.flush()
    
    questions_data = data.get("questions", [])
    for idx, q_data in enumerate(questions_data, start=1):
        q_id = f"Q-{uuid.uuid4().hex[:8].upper()}"
        opts = q_data.get("options_json", "[]")
        opts_str = json.dumps(opts, ensure_ascii=False) if isinstance(opts, (list, dict)) else str(opts)
            
        corr = q_data.get("correct_answers_json", "")
        corr_str = json.dumps(corr, ensure_ascii=False) if isinstance(corr, (list, dict)) else str(corr)
            
        new_q = Question(
            id=q_id,
            exam_id=new_exam.id,
            ordering=int(q_data.get("ordering", idx)),
            type=str(q_data.get("type", "single_choice")),
            prompt_markdown=str(q_data.get("prompt_markdown", "")),
            points=float(q_data.get("points", 2.0)),
            negative_penalty=float(q_data.get("negative_penalty", 0.0)),
            time_limit_seconds=q_data.get("time_limit_seconds"),
            options_json=opts_str,
            correct_answers_json=corr_str
        )
        db.add(new_q)
        
    db.commit()
    db.refresh(new_exam)
    return new_exam

@router.get("/templates")
def list_exam_templates(
    current_user: User = Depends(require_teacher_or_admin)
):
    """Liste les modèles d'examen JSON disponibles dans le répertoire de templates."""
    if not TEMPLATES_DIR.exists():
        return []
        
    templates = []
    for f in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            templates.append({
                "template_id": f.stem,
                "filename": f.name,
                "title": data.get("title", f.stem),
                "module_code": data.get("module_code", ""),
                "duration_minutes": data.get("duration_minutes", 45),
                "global_points": data.get("global_points", 20.0),
                "question_count": len(data.get("questions", [])),
                "group_ids": data.get("group_ids", [])
            })
        except Exception:
            continue
    return templates

@router.post("/templates/{template_id}/load", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def load_exam_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Charge et instancie un modèle d'examen officiel en base de données."""
    candidate_files = [
        TEMPLATES_DIR / f"{template_id}.json",
        TEMPLATES_DIR / template_id,
    ]
    target_file = None
    for cf in candidate_files:
        if cf.exists() and cf.is_file():
            target_file = cf
            break
            
    if not target_file:
        for f in TEMPLATES_DIR.glob("*.json"):
            if template_id.lower() in f.stem.lower() or f.name.lower() == template_id.lower():
                target_file = f
                break
                
    if not target_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modèle d'examen '{template_id}' introuvable."
        )
        
    with open(target_file, "r", encoding="utf-8") as fp:
        data = json.load(fp)
        
    new_exam = _create_exam_from_template_dict(data, db, current_user)
    tot_pts = round(sum(q.points for q in new_exam.questions), 2)
    return ExamResponse(
        id=new_exam.id,
        module_code=new_exam.module_code,
        title=new_exam.title,
        exam_type=getattr(new_exam, "exam_type", "theoretical") or "theoretical",
        instructions=new_exam.instructions,
        duration_minutes=new_exam.duration_minutes,
        global_points=new_exam.global_points,
        total_question_points=tot_pts,
        passing_score=getattr(new_exam, "passing_score", 10.0) or 10.0,
        navigation_mode=new_exam.navigation_mode,
        shuffle_questions=new_exam.shuffle_questions,
        shuffle_options=new_exam.shuffle_options,
        partial_credit_enabled=new_exam.partial_credit_enabled,
        default_negative_penalty=new_exam.default_negative_penalty,
        created_by=new_exam.created_by,
        created_at=new_exam.created_at,
        question_count=len(new_exam.questions),
        assigned_groups=[g.id for g in new_exam.groups]
    )

@router.post("/import-template", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def import_exam_template_payload(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Importe un examen complet depuis un objet JSON téléversé par l'enseignant."""
    new_exam = _create_exam_from_template_dict(payload, db, current_user)
    tot_pts = round(sum(q.points for q in new_exam.questions), 2)
    return ExamResponse(
        id=new_exam.id,
        module_code=new_exam.module_code,
        title=new_exam.title,
        exam_type=getattr(new_exam, "exam_type", "theoretical") or "theoretical",
        instructions=new_exam.instructions,
        duration_minutes=new_exam.duration_minutes,
        global_points=new_exam.global_points,
        total_question_points=tot_pts,
        passing_score=getattr(new_exam, "passing_score", 10.0) or 10.0,
        navigation_mode=new_exam.navigation_mode,
        shuffle_questions=new_exam.shuffle_questions,
        shuffle_options=new_exam.shuffle_options,
        partial_credit_enabled=new_exam.partial_credit_enabled,
        default_negative_penalty=new_exam.default_negative_penalty,
        created_by=new_exam.created_by,
        created_at=new_exam.created_at,
        question_count=len(new_exam.questions),
        assigned_groups=[g.id for g in new_exam.groups]
    )

@router.get("/{exam_id}", response_model=ExamDetailResponse)
def get_exam_detail(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Récupère un examen complet avec l'ensemble de ses questions et barèmes."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
        
    _check_module_permission(current_user, exam.module_code)
    
    tot_pts = round(sum(q.points for q in exam.questions), 2)
    return ExamDetailResponse(
        id=exam.id,
        module_code=exam.module_code,
        title=exam.title,
        exam_type=getattr(exam, "exam_type", "theoretical") or "theoretical",
        instructions=exam.instructions,
        duration_minutes=exam.duration_minutes,
        global_points=exam.global_points,
        total_question_points=tot_pts,
        passing_score=getattr(exam, "passing_score", 10.0) or 10.0,
        navigation_mode=exam.navigation_mode,
        shuffle_questions=exam.shuffle_questions,
        shuffle_options=exam.shuffle_options,
        partial_credit_enabled=exam.partial_credit_enabled,
        default_negative_penalty=exam.default_negative_penalty,
        created_by=exam.created_by,
        created_at=exam.created_at,
        question_count=len(exam.questions),
        assigned_groups=[g.id for g in exam.groups],
        questions=[QuestionResponse.model_validate(q) for q in exam.questions]
    )

@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: str,
    payload: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Met à jour les paramètres d'un examen."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
        
    _check_module_permission(current_user, exam.module_code)
    
    if payload.title is not None:
        exam.title = payload.title.strip()
    if payload.exam_type is not None:
        exam.exam_type = payload.exam_type
    if payload.instructions is not None:
        exam.instructions = payload.instructions
    if payload.duration_minutes is not None:
        exam.duration_minutes = payload.duration_minutes
    if payload.global_points is not None:
        exam.global_points = payload.global_points
    if payload.passing_score is not None and hasattr(exam, "passing_score"):
        exam.passing_score = payload.passing_score
    if payload.shuffle_questions is not None:
        exam.shuffle_questions = payload.shuffle_questions
    if payload.shuffle_options is not None:
        exam.shuffle_options = payload.shuffle_options
    if payload.partial_credit_enabled is not None:
        exam.partial_credit_enabled = payload.partial_credit_enabled
    if payload.default_negative_penalty is not None:
        exam.default_negative_penalty = payload.default_negative_penalty
        
    if payload.group_ids is not None:
        exam.groups.clear()
        if payload.group_ids:
            groups = db.query(Group).filter(Group.id.in_(payload.group_ids)).all()
            exam.groups.extend(groups)
            
    db.commit()
    db.refresh(exam)
    tot_pts = round(sum(q.points for q in exam.questions), 2)
    return ExamResponse(
        id=exam.id,
        module_code=exam.module_code,
        title=exam.title,
        exam_type=getattr(exam, "exam_type", "theoretical") or "theoretical",
        instructions=exam.instructions,
        duration_minutes=exam.duration_minutes,
        global_points=exam.global_points,
        total_question_points=tot_pts,
        passing_score=getattr(exam, "passing_score", 10.0) or 10.0,
        navigation_mode=exam.navigation_mode,
        shuffle_questions=exam.shuffle_questions,
        shuffle_options=exam.shuffle_options,
        partial_credit_enabled=exam.partial_credit_enabled,
        default_negative_penalty=exam.default_negative_penalty,
        created_by=exam.created_by,
        created_at=exam.created_at,
        question_count=len(exam.questions),
        assigned_groups=[g.id for g in exam.groups]
    )

@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Supprime un examen et toutes ses questions rattachées."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)
    
    db.delete(exam)
    db.commit()
    return None

@router.get("/{exam_id}/validate")
def validate_exam(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Vérifie la validité de l'examen avant activation ou lancement :
    - Nombre de questions > 0
    - Respect strict du type d'épreuve (théorique vs pratique)
    - Cohérence du barème des questions vs note globale
    - Présence des tests publics (>= 2) et cachés (>= 10) pour les défis pratiques
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    errors = []
    warnings = []
    q_count = len(exam.questions)
    total_points = round(sum(q.points for q in exam.questions), 2)
    exam_type = getattr(exam, "exam_type", "theoretical") or "theoretical"
    passing_score = getattr(exam, "passing_score", 10.0) or 10.0

    if q_count == 0:
        errors.append("L'examen ne contient aucune question.")

    if exam_type == "theoretical":
        coding_qs = [q.id for q in exam.questions if q.type in ["coding", "code"]]
        if coding_qs:
            errors.append(f"Une épreuve théorique ne peut pas contenir de défis de programmation ({len(coding_qs)} question(s) détectée(s)).")
    elif exam_type == "practical":
        non_coding_qs = [q.id for q in exam.questions if q.type not in ["coding", "code"]]
        if non_coding_qs:
            errors.append(f"Une épreuve pratique doit contenir exclusivement des défis de programmation ({len(non_coding_qs)} question(s) non conforme(s) détectée(s)).")

        for q in exam.questions:
            if q.type in ["coding", "code"]:
                try:
                    opts = json.loads(q.options_json) if isinstance(q.options_json, str) else (q.options_json or {})
                    pub = opts.get("public_tests", []) if isinstance(opts, dict) else []
                    corr = json.loads(q.correct_answers_json) if isinstance(q.correct_answers_json, str) else (q.correct_answers_json or [])
                    tot_corr = len(corr) if isinstance(corr, list) else len(corr.get("hidden_tests", []))
                    if len(pub) < 2:
                        warnings.append(f"Question {q.id} : Moins de 2 tests publics ({len(pub)} présent(s)).")
                    if tot_corr < 10:
                        warnings.append(f"Question {q.id} : Moins de 10 tests cachés ({tot_corr} présent(s)).")
                except Exception:
                    pass

    if q_count > 0 and total_points != exam.global_points:
        warnings.append(f"Le total des points des questions ({total_points}) ne correspond pas au barème global ({exam.global_points}).")

    valid = len(errors) == 0
    return {
        "valid": valid,
        "exam_id": exam.id,
        "exam_type": exam_type,
        "question_count": q_count,
        "total_points": total_points,
        "global_points": exam.global_points,
        "passing_score": passing_score,
        "errors": errors,
        "warnings": warnings
    }

# --- Gestion des Questions dans un Examen ---

@router.post("/{exam_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    exam_id: str,
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Ajoute une question à un examen."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    # Validation stricte du type d'épreuve (Théorique vs Pratique)
    exam_type = getattr(exam, "exam_type", "theoretical") or "theoretical"
    if exam_type == "theoretical" and payload.type in ["coding", "code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une épreuve théorique ne peut pas contenir de défi de programmation Python. Choisissez une épreuve pratique."
        )
    if exam_type == "practical" and payload.type not in ["coding", "code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une épreuve pratique doit contenir exclusivement des défis de programmation Python."
        )
    
    q_id = f"Q-{uuid.uuid4().hex[:8].upper()}"
    new_q = Question(
        id=q_id,
        exam_id=exam.id,
        ordering=payload.ordering,
        type=payload.type,
        prompt_markdown=payload.prompt_markdown,
        points=payload.points,
        negative_penalty=payload.negative_penalty,
        time_limit_seconds=payload.time_limit_seconds,
        options_json=payload.options_json,
        correct_answers_json=payload.correct_answers_json
    )
    db.add(new_q)
    db.commit()
    db.refresh(new_q)
    return new_q

@router.put("/{exam_id}/questions/{q_id}", response_model=QuestionResponse)
def update_question(
    exam_id: str,
    q_id: str,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Met à jour une question existante."""
    question = db.query(Question).filter(Question.id == q_id, Question.exam_id == exam_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable.")
    _check_module_permission(current_user, question.exam.module_code)

    if payload.type is not None:
        exam_type = getattr(question.exam, "exam_type", "theoretical") or "theoretical"
        if exam_type == "theoretical" and payload.type in ["coding", "code"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Une épreuve théorique ne peut pas contenir de défi de programmation Python. Choisissez une épreuve pratique."
            )
        if exam_type == "practical" and payload.type not in ["coding", "code"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Une épreuve pratique doit contenir exclusivement des défis de programmation Python."
            )
        question.type = payload.type
    
    if payload.ordering is not None:
        question.ordering = payload.ordering
    if payload.prompt_markdown is not None:
        question.prompt_markdown = payload.prompt_markdown
    if payload.points is not None:
        question.points = payload.points
    if payload.negative_penalty is not None:
        question.negative_penalty = payload.negative_penalty
    if payload.time_limit_seconds is not None:
        question.time_limit_seconds = payload.time_limit_seconds
    if payload.options_json is not None:
        question.options_json = payload.options_json
    if payload.correct_answers_json is not None:
        question.correct_answers_json = payload.correct_answers_json
        
    db.commit()
    db.refresh(question)
    return question

@router.delete("/{exam_id}/questions/{q_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    exam_id: str,
    q_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Supprime une question d'un examen."""
    question = db.query(Question).filter(Question.id == q_id, Question.exam_id == exam_id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question introuvable.")
    _check_module_permission(current_user, question.exam.module_code)
    
    db.delete(question)
    db.commit()
    return None

@router.put("/{exam_id}/questions/reorder")
def reorder_exam_questions(
    exam_id: str,
    payload: Any = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Réordonne en bloc les questions d'un examen en mettant à jour le champ ordering.
    Accepte soit {"question_orders": [{"id": ..., "display_order": ...}]},
    soit {"items": [{"id": ..., "ordering": ...}]},
    soit une liste directe [{"id": ..., "display_order": ...}].
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    items = []
    if isinstance(payload, dict):
        items = payload.get("question_orders") or payload.get("items") or payload.get("questions") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = getattr(payload, "question_orders", None) or getattr(payload, "items", None) or []

    if not items:
        return {"success": True, "reordered_count": 0, "message": "Aucun ordre à mettre à jour."}

    updated_count = 0
    for it in items:
        qid = it.get("id") if isinstance(it, dict) else getattr(it, "id", None)
        ord_val = None
        if isinstance(it, dict):
            ord_val = it.get("display_order") if it.get("display_order") is not None else it.get("ordering")
        else:
            ord_val = getattr(it, "display_order", None) or getattr(it, "ordering", None)

        if qid and ord_val is not None:
            q = db.query(Question).filter(Question.id == qid, Question.exam_id == exam_id).first()
            if q:
                q.ordering = int(ord_val)
                updated_count += 1

    db.commit()
    return {
        "success": True,
        "reordered_count": updated_count,
        "message": f"Ordre de {updated_count} question(s) mis à jour avec succès."
    }

@router.post("/{exam_id}/questions/import-json")
def import_questions_json(
    exam_id: str,
    payload: List[QuestionCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Importe un lot de questions structurées depuis un tableau JSON."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    # Validation stricte du type d'épreuve (Théorique vs Pratique)
    exam_type = getattr(exam, "exam_type", "theoretical") or "theoretical"
    for q_item in payload:
        if exam_type == "theoretical" and q_item.type in ["coding", "code"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Une épreuve théorique ne peut pas contenir de défi de programmation Python. Choisissez une épreuve pratique."
            )
        if exam_type == "practical" and q_item.type not in ["coding", "code"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Une épreuve pratique doit contenir exclusivement des défis de programmation Python."
            )
    
    added_count = 0
    for q_data in payload:
        q_id = f"Q-{uuid.uuid4().hex[:8].upper()}"
        new_q = Question(
            id=q_id,
            exam_id=exam.id,
            ordering=q_data.ordering,
            type=q_data.type,
            prompt_markdown=q_data.prompt_markdown,
            points=q_data.points,
            negative_penalty=q_data.negative_penalty,
            time_limit_seconds=q_data.time_limit_seconds,
            options_json=q_data.options_json,
            correct_answers_json=q_data.correct_answers_json
        )
        db.add(new_q)
        added_count += 1
        
    db.commit()
    return {"success": True, "imported_count": added_count, "message": f"{added_count} question(s) importée(s) avec succès."}

@router.get("/{exam_id}/questions/export-json")
def export_questions_json(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Exporte l'ensemble des questions d'un examen sous forme de JSON structuré."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    questions = db.query(Question).filter(Question.exam_id == exam_id).order_by(Question.ordering).all()
    results = []
    for q in questions:
        results.append({
            "ordering": q.ordering,
            "type": q.type,
            "prompt_markdown": q.prompt_markdown,
            "points": q.points,
            "negative_penalty": q.negative_penalty,
            "time_limit_seconds": q.time_limit_seconds,
            "options_json": q.options_json,
            "correct_answers_json": q.correct_answers_json
        })
    return results

@router.get("/{exam_id}/item-analysis")
def get_exam_item_analysis_endpoint(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Retourne l'analyse psychométrique et l'indice de discrimination des questions (Item Analysis)
    pour l'ensemble des tentatives soumises à cet examen.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)
    
    return calculate_exam_item_analysis(exam_id=exam.id, db=db)

@router.get("/{exam_id}/item-analysis/csv")
def export_exam_item_analysis_csv_endpoint(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Exporte l'analyse statistique et psychométrique des questions au format CSV UTF-8 BOM.
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    analysis = calculate_exam_item_analysis(exam_id=exam.id, db=db)
    csv_content = generate_item_analysis_csv(analysis)
    
    filename = f"analyse_questions_{exam.module_code}_{exam.id}.csv"
    return StreamingResponse(
        iter([csv_content.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



# ==============================================================================
# Générateur Automatique d'Épreuves Python (Banque d'Exercices)
# ==============================================================================

class PythonExamGenerateRequest(BaseModel):
    title: str
    exam_type: str = "theoretical"  # 'theoretical' | 'practical'
    duration_minutes: int = 45
    chapter_ids: Optional[List[str]] = None
    difficulty_counts: Optional[Dict[str, int]] = None
    assigned_groups: Optional[List[str]] = None
    group_ids: Optional[List[str]] = None
    target_count: Optional[int] = None
    room_id: Optional[str] = "SALLE-CENTRAL-01"

@router.get("/python/bank-stats")
def get_python_question_bank_statistics(
    current_user: User = Depends(require_teacher_or_admin)
):
    """Retourne les statistiques de la banque d'exercices Python (par chapitre et difficulté)."""
    from backend.app.services.python_exam_generator import get_python_bank_stats
    return get_python_bank_stats()

@router.post("/python/generate", status_code=status.HTTP_201_CREATED)
def generate_python_exam_endpoint(
    payload: PythonExamGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Génère automatiquement une épreuve officielle Python depuis la banque d'exercices.
    - Épreuve Théorique : Sélection de 30 questions (priorité aux questions Exams=True),
      chaque étudiant reçoit 20 questions aléatoires.
    - Épreuve Pratique : Sélection de 10 défis (priorité à is_exam=True),
      chaque étudiant reçoit 5 défis aléatoires.
    """
    from backend.app.services.python_exam_generator import generate_python_exam
    new_exam = generate_python_exam(
        db=db,
        title=payload.title,
        exam_type=payload.exam_type,
        duration_minutes=payload.duration_minutes,
        chapter_ids=payload.chapter_ids,
        difficulty_counts=payload.difficulty_counts,
        assigned_groups=payload.assigned_groups or payload.group_ids,
        target_count=payload.target_count,
        created_by=current_user.id
    )

    # Création automatique de la session de salle si demandée
    room_id = payload.room_id or "SALLE-CENTRAL-01"
    session_id = f"SESS-{new_exam.id}"
    existing_sess = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not existing_sess:
        new_sess = ExamSession(
            id=session_id,
            exam_id=new_exam.id,
            room_id=room_id,
            status="active",
            launched_by=current_user.id
        )
        db.add(new_sess)
        db.commit()

    return {
        "success": True,
        "exam_id": new_exam.id,
        "session_id": session_id,
        "title": new_exam.title,
        "exam_type": new_exam.exam_type,
        "duration_minutes": new_exam.duration_minutes,
        "question_count": len(new_exam.questions),
        "questions": [{"id": q.id, "type": q.type} for q in new_exam.questions],
        "message": f"Épreuve Python '{new_exam.title}' ({len(new_exam.questions)} questions/exercices) générée avec succès !"
    }


# ==============================================================================
# Téléchargement des Notes Finales par Examen pour Tous les Étudiants
# ==============================================================================

def _build_exam_all_students_grades(exam: Exam, db: Session) -> Dict[str, Any]:
    """
    Construit le relevé complet des notes finales d'un examen pour TOUS les étudiants
    inscrits dans les classes/groupes assignés à l'examen (ainsi que tout étudiant ayant composé).
    """
    from backend.app.models import StudentAttempt
    import csv
    import io

    assigned_group_ids = [g.id for g in exam.groups] if exam.groups else []
    q_students = db.query(User).filter(User.role == "student")
    if assigned_group_ids:
        enrolled_students = q_students.filter(User.group_id.in_(assigned_group_ids)).order_by(User.group_id, User.full_name).all()
    else:
        enrolled_students = q_students.order_by(User.group_id, User.full_name).all()

    student_map = {s.id: s for s in enrolled_students}

    sessions = db.query(ExamSession).filter(ExamSession.exam_id == exam.id).all()
    session_ids = [s.id for s in sessions]
    attempts = []
    if session_ids:
        attempts = db.query(StudentAttempt).filter(StudentAttempt.session_id.in_(session_ids)).all()

    best_attempt_by_student: Dict[str, StudentAttempt] = {}
    for att in attempts:
        if att.student_id not in student_map and att.student:
            student_map[att.student_id] = att.student
        prev = best_attempt_by_student.get(att.student_id)
        if prev is None:
            best_attempt_by_student[att.student_id] = att
        else:
            prev_mark = prev.final_mark if prev.final_mark is not None else -1.0
            curr_mark = att.final_mark if att.final_mark is not None else -1.0
            if (att.status == "submitted" and prev.status != "submitted") or (curr_mark > prev_mark):
                best_attempt_by_student[att.student_id] = att

    rows = []
    submitted_marks = []
    for stu in sorted(student_map.values(), key=lambda u: (u.group_id or "ZZZ", u.full_name or u.username)):
        att = best_attempt_by_student.get(stu.id)
        if att:
            status_map = {
                "submitted": "Soumis",
                "timed_out": "Temps écoulé",
                "in_progress": "En cours",
                "waiting": "En salle d'attente",
                "suspended": "Suspendu"
            }
            status_label = status_map.get(att.status, att.status)
            raw_score = round(att.raw_score, 2) if att.raw_score is not None else None
            final_mark = round(att.final_mark, 2) if att.final_mark is not None else None
            submitted_at_str = att.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if att.submitted_at else ""
            if final_mark is not None:
                submitted_marks.append(final_mark)
                verdict = "Validé" if final_mark >= 10.0 else "Ajourné"
            else:
                verdict = "En cours"
        else:
            status_label = "Non présenté"
            raw_score = None
            final_mark = None
            submitted_at_str = ""
            verdict = "Absent"

        rows.append({
            "student_id": stu.id,
            "username": stu.username,
            "full_name": stu.full_name,
            "email": stu.email or "",
            "group_id": stu.group_id or "Sans classe",
            "enrollment_year": stu.enrollment_year or "2025-2026",
            "status": status_label,
            "raw_score": raw_score,
            "final_mark": final_mark,
            "verdict": verdict,
            "submitted_at": submitted_at_str
        })

    avg_mark = round(sum(submitted_marks) / len(submitted_marks), 2) if submitted_marks else 0.0
    pass_count = sum(1 for m in submitted_marks if m >= 10.0)
    pass_rate = round((pass_count / len(submitted_marks)) * 100, 1) if submitted_marks else 0.0

    return {
        "exam_id": exam.id,
        "title": exam.title,
        "module_code": exam.module_code,
        "exam_type": getattr(exam, "exam_type", "theoretical") or "theoretical",
        "duration_minutes": exam.duration_minutes,
        "total_students": len(rows),
        "submitted_count": len(submitted_marks),
        "average_mark_20": avg_mark,
        "pass_rate": pass_rate,
        "students": rows
    }


@router.get("/{exam_id}/results")
def get_exam_results_all_students(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """Retourne les notes finales de tous les étudiants inscrits pour cet examen."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)
    return _build_exam_all_students_grades(exam, db)


@router.get("/{exam_id}/results/export-csv")
def export_exam_results_csv_all_students(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Exporte au format CSV (UTF-8 BOM compatible Excel) les notes finales de TOUS les étudiants
    pour un examen donné.
    """
    import csv
    import io

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    report = _build_exam_all_students_grades(exam, db)
    output = io.StringIO()
    output.write("\ufeff")  # BOM UTF-8 pour Excel
    writer = csv.writer(output, delimiter=";")

    volet_label = "Pratique" if report["exam_type"] == "practical" else "Théorique"
    writer.writerow([
        "Code Examen", "Titre Examen", "Module", "Volet",
        "Matricule", "Identifiant", "Nom Complet", "Email", "Classe / Groupe", "Promotion",
        "Statut Copie", "Score Brut", "Note Finale (/20)", "Décision", "Date de Soumission"
    ])
    for r in report["students"]:
        writer.writerow([
            report["exam_id"],
            report["title"],
            report["module_code"],
            volet_label,
            r["student_id"],
            r["username"],
            r["full_name"],
            r["email"],
            r["group_id"],
            r["enrollment_year"],
            r["status"],
            f"{r['raw_score']:.2f}" if r["raw_score"] is not None else "N/A",
            f"{r['final_mark']:.2f}" if r["final_mark"] is not None else "ABS",
            r["verdict"],
            r["submitted_at"] or "-"
        ])

    filename = f"notes_finales_{exam.module_code}_{exam.id}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/{exam_id}/results/export-pdf")
def export_exam_results_pdf_all_students(
    exam_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin)
):
    """
    Génère et télécharge le Procès-Verbal officiel PDF des notes finales de tous les étudiants
    pour un examen donné.
    """
    import io
    from datetime import datetime
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen introuvable.")
    _check_module_permission(current_user, exam.module_code)

    report = _build_exam_all_students_grades(exam, db)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ExamPVTitle",
        parent=styles["Heading1"],
        fontSize=15,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )
    sub_style = ParagraphStyle(
        "ExamPVSub",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=12
    )

    volet_label = "Pratique (Machine)" if report["exam_type"] == "practical" else "Théorique (QCM / Synthèse)"
    elements = [
        Paragraph(f"PROCÈS-VERBAL DES NOTES FINALES — {report['title']}", title_style),
        Paragraph(
            f"<b>Module :</b> {report['module_code']} &nbsp;|&nbsp; "
            f"<b>Volet :</b> {volet_label} &nbsp;|&nbsp; "
            f"<b>Inscrits :</b> {report['total_students']} &nbsp;|&nbsp; "
            f"<b>Copies soumises :</b> {report['submitted_count']} &nbsp;|&nbsp; "
            f"<b>Moyenne :</b> {report['average_mark_20']:.2f}/20 &nbsp;|&nbsp; "
            f"<b>Édité le :</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            sub_style
        ),
        Spacer(1, 0.3 * cm)
    ]

    table_data = [[
        "Matricule", "Identifiant", "Nom & Prénom", "Classe",
        "Statut", "Note Finale (/20)", "Décision", "Horodatage Soumission"
    ]]
    for r in report["students"]:
        table_data.append([
            r["student_id"],
            r["username"],
            r["full_name"],
            r["group_id"],
            r["status"],
            f"{r['final_mark']:.2f} / 20" if r["final_mark"] is not None else "ABS",
            r["verdict"],
            r["submitted_at"] or "-"
        ])

    tbl = Table(table_data, colWidths=[3.2 * cm, 2.8 * cm, 6.0 * cm, 3.0 * cm, 3.2 * cm, 3.2 * cm, 2.6 * cm, 4.2 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("ALIGN", (5, 1), (6, -1), "CENTER"),
    ]))
    elements.append(tbl)
    doc.build(elements)
    buffer.seek(0)

    filename = f"pv_notes_finales_{exam.module_code}_{exam.id}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

