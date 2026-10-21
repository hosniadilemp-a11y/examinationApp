import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union

def normalize_text(text: Optional[str]) -> str:
    """Normalise une chaîne : suppression des espaces superflus, mise en minuscules."""
    if not text:
        return ""
    # Remplacement des espaces multiples par un seul espace et suppression des bordures
    cleaned = re.sub(r'\s+', ' ', text.strip().lower())
    return cleaned

def evaluate_answer(
    q_type: str,
    user_answer: Any,
    correct_answers: Any,
    points: float = 1.0,
    negative_penalty: float = 0.5,
    floor_score: float = 0.0,
    strict_single_penalty: bool = False
) -> Tuple[float, bool, str]:
    """
    Évalue la réponse d'un étudiant selon le type de question et le barème.
    
    Retourne : (awarded_points, is_correct, explanation)
    """
    if points <= 0:
        return 0.0, False, "Question sans points."

    # Désérialisation si nécessaire
    if isinstance(correct_answers, str):
        trimmed_c = correct_answers.strip()
        if trimmed_c.startswith("[") or trimmed_c.startswith("{"):
            try:
                correct_answers = json.loads(trimmed_c)
            except Exception:
                pass

    if isinstance(user_answer, str):
        trimmed_u = user_answer.strip()
        if trimmed_u.startswith("[") or trimmed_u.startswith("{"):
            try:
                user_answer = json.loads(trimmed_u)
            except Exception:
                pass

    # --- 1. Type : Vrai / Faux (Binaire) ---
    if q_type == "boolean":
        # Normalisation en booléen
        def _to_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.strip().lower() in ("true", "vrai", "1", "yes", "oui")
            if isinstance(val, (int, float)):
                return bool(val)
            return None

        u_bool = _to_bool(user_answer)
        c_bool = _to_bool(correct_answers)

        if u_bool is None:
            return 0.0, False, "Aucune réponse fournie."

        if u_bool == c_bool:
            return float(points), True, "Bonne réponse."
        else:
            penalty = -negative_penalty if strict_single_penalty else 0.0
            awarded = max(floor_score, penalty)
            return float(awarded), False, "Réponse incorrecte."

    # --- 2. Type : QCM à Réponse Unique ---
    elif q_type == "single_choice":
        if user_answer is None or str(user_answer).strip() == "":
            return 0.0, False, "Aucune réponse fournie."

        u_choice = str(user_answer).strip()
        c_choice = str(correct_answers).strip() if not isinstance(correct_answers, list) else str(correct_answers[0]).strip()

        if u_choice == c_choice:
            return float(points), True, "Bonne réponse."
        else:
            penalty = -negative_penalty if strict_single_penalty else 0.0
            awarded = max(floor_score, penalty)
            return float(awarded), False, "Option incorrecte choisie."

    # --- 3. Type : QCM à Réponses Multiples (avec crédit partiel et pénalité) ---
    elif q_type == "multi_choice":
        u_picks = user_answer if isinstance(user_answer, list) else []
        c_picks = correct_answers if isinstance(correct_answers, list) else [correct_answers]

        u_set = {str(x).strip() for x in u_picks if str(x).strip()}
        c_set = {str(x).strip() for x in c_picks if str(x).strip()}

        # Cas particulier : aucune bonne réponse requise (question piège)
        if len(c_set) == 0:
            if len(u_set) == 0:
                return float(points), True, "Correct : aucune option ne devait être cochée."
            else:
                raw = -len(u_set) * negative_penalty
                return float(max(floor_score, raw)), False, "Des options erronées ont été cochées."

        # Règle de notation standard :
        # Chaque bonne option cochée = points / N_bonnes
        # Chaque fausse option cochée = -negative_penalty
        val_per_correct = points / len(c_set)
        good_picks = u_set.intersection(c_set)
        bad_picks = u_set.difference(c_set)

        raw_score = (len(good_picks) * val_per_correct) - (len(bad_picks) * negative_penalty)
        final_score = round(max(floor_score, raw_score), 2)
        is_exact = (u_set == c_set)

        feedback = f"{len(good_picks)}/{len(c_set)} bonne(s) réponse(s) trouvée(s)"
        if bad_picks:
            feedback += f", {len(bad_picks)} mauvaise(s) sélection(s) (-{len(bad_picks) * negative_penalty} pts)."
        else:
            feedback += "."

        return float(final_score), is_exact, feedback

    # --- 4. Type : Texte à Trou (Fill-in-the-Blank) ---
    elif q_type == "fill_blank":
        if not user_answer or not str(user_answer).strip():
            return 0.0, False, "Aucun texte saisi."

        u_norm = normalize_text(str(user_answer))
        
        # correct_answers peut être une liste de synonymes ou une seule chaîne
        if isinstance(correct_answers, list):
            valid_norms = [normalize_text(str(c)) for c in correct_answers]
        else:
            valid_norms = [normalize_text(str(correct_answers))]

        if u_norm in valid_norms:
            return float(points), True, "Réponse exacte."
        else:
            return float(floor_score), False, "Le texte saisi ne correspond pas à la réponse attendue."

    # --- 5. Type : Appariement / Correspondance (Matching) ---
    elif q_type == "matching":
        # Structure attendue : dict de paires {"clef_gauche": "clef_droite"}
        if isinstance(user_answer, str):
            try:
                user_answer = json.loads(user_answer.strip())
            except Exception:
                pass
        if isinstance(correct_answers, str):
            try:
                correct_answers = json.loads(correct_answers.strip())
            except Exception:
                pass

        if not isinstance(user_answer, dict) or not isinstance(correct_answers, dict):
            return 0.0, False, "Format d'appariement invalide."

        total_pairs = len(correct_answers)
        if total_pairs == 0:
            return float(points), True, "Aucune paire à associer."

        val_per_pair = points / total_pairs
        good_matches = 0

        # Normaliser les clés et valeurs de l'utilisateur
        norm_user = {str(k).strip(): str(v).strip() for k, v in user_answer.items()}

        for left_k, right_v in correct_answers.items():
            k_clean = str(left_k).strip()
            v_clean = str(right_v).strip()
            u_v = norm_user.get(k_clean)
            if u_v is not None and u_v == v_clean:
                good_matches += 1

        final_score = round(good_matches * val_per_pair, 2)
        is_exact = (good_matches == total_pairs)
        feedback = f"{good_matches}/{total_pairs} association(s) correcte(s)."

        return float(max(floor_score, final_score)), is_exact, feedback

    # --- 6. Type : Exercice de Code Python (HackerRank / AlgoCompiler) ---
    elif q_type in ["coding", "code"]:
        if not user_answer or not str(user_answer).strip():
            return 0.0, False, "Aucun code fourni."

        code_str = str(user_answer)
        
        # Les cas de test sont stockés dans correct_answers sous forme de liste de dictionnaires
        test_cases = []
        if isinstance(correct_answers, list):
            test_cases = correct_answers
        elif isinstance(correct_answers, dict):
            test_cases = correct_answers.get("tests", correct_answers.get("test_cases", []))

        if not test_cases:
            return float(points), True, "Code soumis sans cas de test automatisés."

        from backend.app.services.sandbox_runner import execute_user_code_against_tests
        run_res = execute_user_code_against_tests(code_str, test_cases, timeout_seconds=3.0, mask_hidden_output=False)
        
        total = run_res.get("total_count", 0)
        passed = run_res.get("passed_count", 0)
        all_passed = run_res.get("all_passed", False)
        
        if total > 0:
            awarded = round((passed / total) * points, 2)
        else:
            awarded = 0.0
            
        feedback = f"{passed}/{total} cas de test validés."
        return float(max(floor_score, awarded)), all_passed, feedback

    return 0.0, False, f"Type de question non supporté : '{q_type}'."
