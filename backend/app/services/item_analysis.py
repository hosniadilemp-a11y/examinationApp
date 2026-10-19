import csv
import io
import math
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.app.models import Exam, ExamSession, StudentAttempt, StudentAnswer, Question

def calculate_exam_item_analysis(exam_id: str, db: Session, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcule l'analyse psychométrique et l'indice de discrimination des questions (Item Analysis)
    pour un examen donné ou une session spécifique.
    
    Métriques calculées :
    - Distribution globale : Moyenne, Médiane, Écart-Type, Min, Max, Taux de Réussite.
    - Pour chaque question :
      - Taux de facilité / réussite P (Facility Index)
      - Réussite groupe fort (Pu) vs groupe faible (Pl) - règle de Kelley (top/bottom 27%)
      - Indice de discrimination D = Pu - Pl (-1.0 à +1.0)
      - Diagnostic de discrimination (Excellente, Bonne, Acceptable, Faible, Inversée)
      - Détection des anomalies (D < 0 ou P = 0%)
    """
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return {"error": "Examen introuvable."}

    questions = db.query(Question).filter(Question.exam_id == exam.id).order_by(Question.ordering).all()

    # Récupération des tentatives terminées
    query = db.query(StudentAttempt).join(ExamSession).filter(
        ExamSession.exam_id == exam.id,
        StudentAttempt.status.in_(["submitted", "completed", "timed_out"]),
        StudentAttempt.final_mark.isnot(None)
    )
    if session_id:
        query = query.filter(StudentAttempt.session_id == session_id)

    attempts = query.all()
    total_candidates = len(attempts)

    # Si aucune copie n'a été soumise
    if total_candidates == 0:
        return {
            "exam_id": exam.id,
            "exam_title": exam.title,
            "module_code": exam.module_code,
            "session_id": session_id,
            "total_candidates": 0,
            "global_stats": {
                "mean": 0.0,
                "median": 0.0,
                "std_dev": 0.0,
                "min": 0.0,
                "max": 0.0,
                "pass_rate_pct": 0.0,
                "distinction_rate_pct": 0.0
            },
            "questions_analysis": [{
                "question_id": q.id,
                "ordering": q.ordering,
                "type": q.type,
                "prompt_snippet": q.prompt_markdown[:100] + ("..." if len(q.prompt_markdown) > 100 else ""),
                "points": q.points,
                "total_answers": 0,
                "correct_count": 0,
                "facility_index": 0.0,
                "facility_pct": 0.0,
                "discrimination_index": 0.0,
                "discrimination_quality": "Données insuffisantes",
                "is_anomaly": False,
                "anomaly_reason": None
            } for q in questions],
            "anomalies_count": 0,
            "anomalies": []
        }

    # Calcul des métriques globales de l'examen
    scores = sorted([att.final_mark for att in attempts])
    mean_score = sum(scores) / total_candidates
    
    # Médiane
    if total_candidates % 2 == 1:
        median_score = scores[total_candidates // 2]
    else:
        median_score = (scores[total_candidates // 2 - 1] + scores[total_candidates // 2]) / 2.0

    # Écart-type
    variance = sum((s - mean_score) ** 2 for s in scores) / total_candidates
    std_dev = math.sqrt(variance)

    min_score = min(scores)
    max_score = max(scores)
    pass_count = sum(1 for s in scores if s >= 10.0)
    pass_rate_pct = round((pass_count / total_candidates) * 100.0, 1)
    distinction_count = sum(1 for s in scores if s >= 14.0)
    distinction_rate_pct = round((distinction_count / total_candidates) * 100.0, 1)

    # Règle de Kelley pour la discrimination (Top/Bottom 27% ou moitiés)
    # Tri des tentatives par note finale décroissante
    sorted_attempts = sorted(attempts, key=lambda a: a.final_mark or 0.0, reverse=True)
    if total_candidates >= 6:
        k = max(1, round(total_candidates * 0.27))
    else:
        k = max(1, total_candidates // 2)

    upper_attempts = sorted_attempts[:k]
    lower_attempts = sorted_attempts[-k:]
    upper_attempt_ids = {a.id for a in upper_attempts}
    lower_attempt_ids = {a.id for a in lower_attempts}
    all_attempt_ids = {a.id for a in attempts}

    # Récupération de toutes les réponses pour ces tentatives
    all_answers = db.query(StudentAnswer).filter(
        StudentAnswer.attempt_id.in_(all_attempt_ids)
    ).all()

    # Indexation des réponses : { (question_id, attempt_id): StudentAnswer }
    answers_map: Dict[tuple, StudentAnswer] = {
        (ans.question_id, ans.attempt_id): ans for ans in all_answers
    }

    questions_analysis = []
    anomalies = []

    for q in questions:
        q_answers = [answers_map.get((q.id, att_id)) for att_id in all_attempt_ids if (q.id, att_id) in answers_map]
        total_q_answers = len(q_answers)
        correct_count = sum(1 for ans in q_answers if ans.is_correct is True)
        total_awarded_points = sum(ans.awarded_points or 0.0 for ans in q_answers)

        # Indice de Facilité P (proportion de points obtenus ou de réussite)
        max_possible_points = (total_q_answers * q.points) if (total_q_answers > 0 and q.points > 0) else 1.0
        facility_index = round(total_awarded_points / max_possible_points, 3)
        facility_pct = round(facility_index * 100.0, 1)

        # Calcul de la réussite dans le Groupe Supérieur (Pu) et Inférieur (Pl)
        upper_q_answers = [answers_map.get((q.id, att_id)) for att_id in upper_attempt_ids if (q.id, att_id) in answers_map]
        lower_q_answers = [answers_map.get((q.id, att_id)) for att_id in lower_attempt_ids if (q.id, att_id) in answers_map]

        upper_points = sum(ans.awarded_points or 0.0 for ans in upper_q_answers)
        lower_points = sum(ans.awarded_points or 0.0 for ans in lower_q_answers)

        upper_max = (len(upper_attempts) * q.points) if q.points > 0 else 1.0
        lower_max = (len(lower_attempts) * q.points) if q.points > 0 else 1.0

        p_upper = upper_points / upper_max if upper_max > 0 else 0.0
        p_lower = lower_points / lower_max if lower_max > 0 else 0.0

        # Indice de Discrimination D = Pu - Pl
        discrimination_index = round(p_upper - p_lower, 3)
        # Clamping
        discrimination_index = max(-1.0, min(1.0, discrimination_index))

        # Diagnostic psychométrique
        is_anomaly = False
        anomaly_reason = None

        if discrimination_index >= 0.40:
            quality = "Excellente discrimination"
            quality_badge = "excellent"
        elif discrimination_index >= 0.30:
            quality = "Bonne discrimination"
            quality_badge = "good"
        elif discrimination_index >= 0.20:
            quality = "Discrimination acceptable"
            quality_badge = "acceptable"
        elif discrimination_index >= 0.00:
            quality = "Faible discrimination"
            quality_badge = "weak"
            if facility_pct >= 95.0:
                anomaly_reason = "Question trop facile (taux de réussite ≥ 95%), peu discriminante."
            elif facility_pct <= 10.0:
                is_anomaly = True
                quality_badge = "anomaly"
                anomaly_reason = "Question excessivement difficile (taux de réussite ≤ 10%)."
        else:
            quality = "Anomalie inversée (D < 0)"
            quality_badge = "anomaly"
            is_anomaly = True
            anomaly_reason = (
                f"Discrimination négative (D = {discrimination_index}) : "
                "les candidats les plus faibles ont mieux réussi cette question que les candidats les plus forts. "
                "Vérifier la formulation de l'énoncé ou la clé de correction."
            )

        if is_anomaly:
            anomalies.append({
                "question_id": q.id,
                "ordering": q.ordering,
                "prompt_snippet": q.prompt_markdown[:90] + "...",
                "discrimination_index": discrimination_index,
                "facility_pct": facility_pct,
                "reason": anomaly_reason
            })

        questions_analysis.append({
            "question_id": q.id,
            "ordering": q.ordering,
            "type": q.type,
            "prompt_snippet": q.prompt_markdown[:100] + ("..." if len(q.prompt_markdown) > 100 else ""),
            "prompt_full": q.prompt_markdown,
            "points": q.points,
            "negative_penalty": q.negative_penalty,
            "total_answers": total_q_answers,
            "correct_count": correct_count,
            "avg_awarded_points": round(total_awarded_points / total_q_answers, 2) if total_q_answers > 0 else 0.0,
            "facility_index": facility_index,
            "facility_pct": facility_pct,
            "p_upper": round(p_upper, 3),
            "p_lower": round(p_lower, 3),
            "discrimination_index": discrimination_index,
            "discrimination_quality": quality,
            "quality_badge": quality_badge,
            "is_anomaly": is_anomaly,
            "anomaly_reason": anomaly_reason
        })

    return {
        "exam_id": exam.id,
        "exam_title": exam.title,
        "module_code": exam.module_code,
        "session_id": session_id,
        "total_candidates": total_candidates,
        "upper_group_size": k,
        "lower_group_size": k,
        "global_stats": {
            "mean": round(mean_score, 2),
            "median": round(median_score, 2),
            "std_dev": round(std_dev, 2),
            "min": round(min_score, 2),
            "max": round(max_score, 2),
            "pass_rate_pct": pass_rate_pct,
            "distinction_rate_pct": distinction_rate_pct
        },
        "questions_analysis": questions_analysis,
        "anomalies_count": len(anomalies),
        "anomalies": anomalies
    }

def generate_item_analysis_csv(analysis: Dict[str, Any]) -> str:
    """Génère un export CSV officiel de l'analyse des questions au format UTF-8 avec BOM."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Métadonnées d'en-tête
    writer.writerow(["ANALYSE PSYCHOMETRIQUE DES QUESTIONS D'EXAMEN"])
    writer.writerow(["Titre de l'épreuve", analysis.get("exam_title", "")])
    writer.writerow(["Module", analysis.get("module_code", "")])
    writer.writerow(["Candidats évalués", analysis.get("total_candidates", 0)])
    
    g = analysis.get("global_stats", {})
    writer.writerow([
        f"Moyenne : {g.get('mean', 0.0)}/20",
        f"Médiane : {g.get('median', 0.0)}/20",
        f"Écart-type : {g.get('std_dev', 0.0)}",
        f"Taux d'admission : {g.get('pass_rate_pct', 0.0)}%"
    ])
    writer.writerow([])

    # En-têtes du tableau d'analyse par question
    writer.writerow([
        "N°",
        "Type de Question",
        "Barème (pts)",
        "Pénalité (pts)",
        "Énoncé (Extrait)",
        "Nb Réponses",
        "Réponses Correctes",
        "Taux de Réussite P (%)",
        "Réussite Groupe Fort Pu (%)",
        "Réussite Groupe Faible Pl (%)",
        "Indice de Discrimination D",
        "Diagnostic Psychométrique",
        "Anomalie Détectée"
    ])

    for q in analysis.get("questions_analysis", []):
        prompt_clean = " ".join((q.get("prompt_snippet") or "").splitlines())
        writer.writerow([
            q.get("ordering", ""),
            q.get("type", ""),
            q.get("points", ""),
            q.get("negative_penalty", ""),
            prompt_clean,
            q.get("total_answers", 0),
            q.get("correct_count", 0),
            f"{q.get('facility_pct', 0.0)}%",
            f"{round(q.get('p_upper', 0.0) * 100.0, 1)}%",
            f"{round(q.get('p_lower', 0.0) * 100.0, 1)}%",
            f"{q.get('discrimination_index', 0.0):+.3f}",
            q.get("discrimination_quality", ""),
            q.get("anomaly_reason") or "Non"
        ])

    return output.getvalue()

