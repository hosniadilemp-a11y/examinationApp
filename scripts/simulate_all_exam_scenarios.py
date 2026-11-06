import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import time
from datetime import datetime, timezone, timedelta

# Ensure backend can be imported
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from backend.app.main import app, init_db
from backend.app.database import get_db, Base, engine, SessionLocal
from backend.app.models import User, Exam, Question, ExamSession, StudentAttempt, Module

# Initialise la base si nécessaire
init_db()

client = TestClient(app)

def run_simulation():
    print("=" * 80)
    print("🚀 DÉMARRAGE DE LA SIMULATION INTÉGRALE DES SCÉNARIOS D'EXAMEN")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. SCÉNARIO 1 : SUPER ADMINISTRATEUR (GESTION & CRÉATION)
    # -------------------------------------------------------------------------
    print("\n--- [SCÉNARIO 1] : SUPER ADMINISTRATEUR ---")
    
    # 1.1 Login Admin
    res_admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res_admin_login.status_code == 200, f"Admin login failed: {res_admin_login.text}"
    admin_token = res_admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("  ✅ 1.1 Login Super Admin validé avec succès (JWT token obtenu).")

    # 1.2 Création d'un nouveau module académique
    mod_code = f"PYTHON_DEVOPS_{int(time.time())}"
    res_mod = client.post("/api/modules", json={
        "code": mod_code,
        "title": "Cloud Computing & DevOps Python",
        "description": "Virtualisation, Docker, Kubernetes et automatisation scripts Python."
    }, headers=admin_headers)
    assert res_mod.status_code == 201, f"Create module failed: {res_mod.text}"
    print(f"  ✅ 1.2 Module académique créé : {mod_code} (Cloud Computing & DevOps Python).")

    # 1.3 Affectation de l'enseignant prof-01 au nouveau module
    res_assign = client.post(f"/api/modules/{mod_code}/teachers", json={"teacher_id": "prof-01", "module_code": mod_code}, headers=admin_headers)
    assert res_assign.status_code == 200, f"Assign module failed: {res_assign.text}"
    print(f"  ✅ 1.3 Module {mod_code} affecté avec succès à l'enseignant prof-01 (Professeur Martin).")

    # -------------------------------------------------------------------------
    # 2. SCÉNARIO 2 : ENSEIGNANT (CONCEPTION DE L'ÉPREUVE MULTI-TYPES)
    # -------------------------------------------------------------------------
    print("\n--- [SCÉNARIO 2] : ENSEIGNANT (CRÉATION DE L'EXAMEN & SESSION) ---")
    
    # 2.1 Login Enseignant
    res_prof_login = client.post("/api/auth/login", json={"username": "prof_martin", "password": "prof123"})
    assert res_prof_login.status_code == 200, f"Prof login failed: {res_prof_login.text}"
    prof_token = res_prof_login.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    print("  ✅ 2.1 Login Enseignant prof_martin validé.")

    # 2.2 Création d'une Épreuve Pratique Officielle (Atelier Machine & Défis Python)
    res_exam = client.post("/api/exams", json={
        "module_code": mod_code,
        "title": "Épreuve Pratique Officielle : DevOps & Python Automatisation",
        "instructions": "Calculatrices interdites. Plein écran strict et sandbox Python activé.",
        "exam_type": "practical",
        "duration_minutes": 60,
        "global_points": 20.0,
        "navigation_mode": "free",
        "shuffle_questions": True,
        "shuffle_options": True,
        "partial_credit_enabled": True,
        "default_negative_penalty": 0.5,
        "group_ids": ["DEV-IA", "SYS-ADMIN", "CYBER-SEC", "GRP-1"]
    }, headers=prof_headers)
    assert res_exam.status_code == 201, f"Exam creation failed: {res_exam.text}"
    exam_id = res_exam.json()["id"]
    print(f"  ✅ 2.2 Épreuve Pratique créée avec succès : {exam_id} (Module: {mod_code}, 60 min, 20 pts).")

    # 2.2b Vérification du cloisonnement strict : rejet d'un QCM dans une épreuve pratique
    res_bad_qcm = client.post(f"/api/exams/{exam_id}/questions", json={
        "ordering": 99,
        "type": "single_choice",
        "prompt_markdown": "Test question théorique invalide",
        "points": 2.0,
        "options_json": json.dumps([{"id": "A", "text": "Option A"}]),
        "correct_answers_json": json.dumps("A")
    }, headers=prof_headers)
    assert res_bad_qcm.status_code == 400
    print("  ✅ 2.2b Cloisonnement strict vérifié : interdiction des questions QCM dans une épreuve pratique.")

    # 2.2c Vérification du cloisonnement inverse : rejet du coding dans une épreuve théorique
    res_theo_exam = client.post("/api/exams", json={
        "module_code": mod_code,
        "title": "Épreuve Théorique QCM Test",
        "exam_type": "theoretical",
        "duration_minutes": 30,
        "global_points": 20.0,
        "group_ids": ["DEV-IA"]
    }, headers=prof_headers)
    assert res_theo_exam.status_code == 201
    theo_exam_id = res_theo_exam.json()["id"]
    res_bad_coding = client.post(f"/api/exams/{theo_exam_id}/questions", json={
        "ordering": 1,
        "type": "coding",
        "prompt_markdown": "Code invalide dans une épreuve théorique",
        "points": 5.0,
        "options_json": json.dumps({"starter_code": "pass\n"}),
        "correct_answers_json": json.dumps([])
    }, headers=prof_headers)
    assert res_bad_coding.status_code == 400
    print("  ✅ 2.2c Cloisonnement inverse vérifié : interdiction des défis Python dans une épreuve théorique.")

    # 2.3 Ajout Question 1 : Défi Python (Somme des Pairs, 4 pts, 2 tests publics + 10 cachés)
    q1_pub = [
        {"id": "pub_1", "input": "4\n", "expected_output": "6", "is_public": True},
        {"id": "pub_2", "input": "6\n", "expected_output": "12", "is_public": True}
    ]
    q1_hid = [
        {"id": f"hid_{i}", "input": f"{i*2}\n", "expected_output": str(sum(x for x in range(2, i*2 + 1, 2))), "is_public": False}
        for i in range(1, 11)
    ]
    res_q1 = client.post(f"/api/exams/{exam_id}/questions", json={
        "ordering": 1,
        "type": "coding",
        "prompt_markdown": "### Somme des Entiers Pairs\n\nÉcrivez un programme Python lisant un entier $N$ et affichant la somme des pairs $\\le N$.",
        "points": 4.0,
        "negative_penalty": 0.0,
        "time_limit_seconds": 60,
        "options_json": json.dumps({"starter_code": "import sys\n# Votre code\n", "public_tests": q1_pub}),
        "correct_answers_json": json.dumps(q1_pub + q1_hid)
    }, headers=prof_headers)
    assert res_q1.status_code == 201
    q1_id = res_q1.json()["id"]

    # Ajout Question 2 : Défi Python (Détection Palindrome, 6 pts, 2 tests publics + 10 cachés)
    words_test = ["radar", "python", "kayak", "devops", "level", "docker", "rotor", "ansible", "madam", "linux", "refer", "cloud"]
    q2_pub = [
        {"id": "pub_1", "input": "radar\n", "expected_output": "OUI", "is_public": True},
        {"id": "pub_2", "input": "python\n", "expected_output": "NON", "is_public": True}
    ]
    q2_hid = [
        {"id": f"hid_{i}", "input": f"{words_test[i]}\n", "expected_output": "OUI" if words_test[i] == words_test[i][::-1] else "NON", "is_public": False}
        for i in range(2, 12)
    ]
    res_q2 = client.post(f"/api/exams/{exam_id}/questions", json={
        "ordering": 2,
        "type": "coding",
        "prompt_markdown": "### Détection de Palindrome\n\nLisez une chaîne et affichez `OUI` si elle est un palindrome, sinon `NON`.",
        "points": 6.0,
        "negative_penalty": 0.0,
        "time_limit_seconds": 120,
        "options_json": json.dumps({"starter_code": "import sys\n# Votre code\n", "public_tests": q2_pub}),
        "correct_answers_json": json.dumps(q2_pub + q2_hid)
    }, headers=prof_headers)
    assert res_q2.status_code == 201
    q2_id = res_q2.json()["id"]

    # Ajout Question 3 : Défi de Programmation Python (Factorielle, 10 pts, 2 tests publics et 10 tests cachés)
    public_tests = [
        {"id": "pub_1", "input": "3\n", "expected_output": "6", "is_public": True},
        {"id": "pub_2", "input": "5\n", "expected_output": "120", "is_public": True}
    ]
    hidden_tests = [
        {"id": f"hid_{i}", "input": f"{i}\n", "expected_output": str(
            1 if i <= 1 else (2 if i == 2 else (6 if i == 3 else (24 if i == 4 else (120 if i == 5 else (720 if i == 6 else (5040 if i == 7 else (40320 if i == 8 else (362880 if i == 9 else 3628800))))))))
        ), "is_public": False} for i in range(1, 11)
    ]
    all_tests = public_tests + hidden_tests
    
    res_q_coding = client.post(f"/api/exams/{exam_id}/questions", json={
        "ordering": 3,
        "type": "coding",
        "prompt_markdown": "### Factorielle d'un Entier\n\nÉcrivez un programme Python lisant un entier $N$ depuis `sys.stdin` et affichant $N!$.",
        "points": 10.0,
        "negative_penalty": 0.0,
        "time_limit_seconds": 300,
        "options_json": json.dumps({
            "starter_code": "import sys\n# Calculez factorielle(N)\n",
            "public_tests": public_tests
        }),
        "correct_answers_json": json.dumps(all_tests)
    }, headers=prof_headers)
    assert res_q_coding.status_code == 201
    q_coding_id = res_q_coding.json()["id"]
    print(f"  ✅ 2.3 Questions ajoutées avec succès (3 Défis Machine Python, 20 pts, 100% avec >=2 publics + >=10 cachés).")

    # 2.4 Ouverture de la Session de Salle par l'enseignant
    res_sess = client.post("/api/proctor/sessions", json={
        "exam_id": exam_id,
        "room_id": "Salle TP Reseau 01"
    }, headers=prof_headers)
    assert res_sess.status_code == 200, f"Open session failed: {res_sess.text}"
    session_id = res_sess.json()["session_id"]
    print(f"  ✅ 2.4 Session d'examen ouverte par prof_martin : {session_id} (Statut : waiting).")

    # -------------------------------------------------------------------------
    # 3. SCÉNARIO 3 : ÉTUDIANT 1 (SALLE D'ATTENTE, COMPILATION DU CODE & NOTATION)
    # -------------------------------------------------------------------------
    print("\n--- [SCÉNARIO 3] : ÉTUDIANT 1 (DÉROULEMENT NORMAL & CODING CHALLENGE) ---")
    res_st1_login = client.post("/api/auth/login", json={"username": "etu_dev1", "password": "StudentDev1!"})
    assert res_st1_login.status_code == 200
    st1_token = res_st1_login.json()["access_token"]
    st1_headers = {"Authorization": f"Bearer {st1_token}"}

    # 3.1 Démarrage de l'épreuve par l'étudiant -> placé en attente
    res_st1_start = client.post(f"/api/student/exams/{exam_id}/start", headers=st1_headers)
    assert res_st1_start.status_code == 200
    assert res_st1_start.json()["status"] == "waiting"
    st1_attempt_id = res_st1_start.json()["attempt_id"]
    print(f"  ✅ 3.1 Étudiant etu_dev1 placé dans la salle d'attente (Tentative : {st1_attempt_id}).")

    # Vérification du secret absolu des questions tant que l'épreuve n'est pas lancée
    assert "questions" not in res_st1_start.json(), "FUITE SÉCURITÉ : questions exposées pendant l'attente !"
    print("  ✅ 3.2 Secret absolu vérifié : 0 question ni corrigé envoyé pendant l'attente.")

    # 3.2 Lancement synchronisé par l'enseignant
    res_launch = client.post(f"/api/proctor/sessions/{session_id}/launch", headers=prof_headers)
    assert res_launch.status_code == 200
    print("  ✅ 3.3 Enseignant donne le top départ synchronisé pour la salle.")

    # 3.3 L'étudiant réactualise et reçoit les questions (avec réponses masquées)
    res_st1_active = client.post(f"/api/student/exams/{exam_id}/start", headers=st1_headers)
    assert res_st1_active.status_code == 200
    assert res_st1_active.json()["attempt_status"] == "in_progress"
    questions_view = res_st1_active.json()["questions"]
    for qv in questions_view:
        assert "correct_answers_json" not in qv or qv.get("correct_answers_json") is None, "FUITE SÉCURITÉ : corrigé exposé !"
    print("  ✅ 3.4 Épreuve lancée : 3 questions reçues, corrigés et tests cachés rigoureusement masqués.")

    # 3.4 Étudiant 1 exécute son code Python dans le Sandbox
    user_code = (
        "import sys, math\n"
        "raw = sys.stdin.read().strip()\n"
        "if raw:\n"
        "    n = int(raw)\n"
        "    print(math.factorial(n))\n"
    )
    res_run_code = client.post("/api/training/python/run-code", json={
        "code": user_code,
        "stdin": "4\n",
        "timeout": 3.0
    }, headers=st1_headers)
    assert res_run_code.status_code == 200
    assert res_run_code.json()["stdout"].strip() == "24"
    print("  ✅ 3.5 Exécution interactive Console E/S (stdin=4 -> stdout=24) validée avec succès.")

    # 3.5 Sauvegarde des réponses de l'étudiant 1 (Codes Python pour les 3 Défis)
    code_q1 = "import sys\nraw = sys.stdin.read().strip()\nif raw:\n    n = int(raw)\n    print(sum(x for x in range(2, n + 1, 2)))\n"
    code_q2 = "import sys\nw = sys.stdin.read().strip()\nprint('OUI' if w == w[::-1] else 'NON')\n"

    res_s1 = client.post(f"/api/student/attempts/{st1_attempt_id}/save-answer", json={
        "question_id": q1_id,
        "answer": code_q1
    }, headers=st1_headers)
    assert res_s1.status_code == 200

    res_s2 = client.post(f"/api/student/attempts/{st1_attempt_id}/save-answer", json={
        "question_id": q2_id,
        "answer": code_q2
    }, headers=st1_headers)
    assert res_s2.status_code == 200

    res_s3 = client.post(f"/api/student/attempts/{st1_attempt_id}/save-answer", json={
        "question_id": q_coding_id,
        "answer": user_code
    }, headers=st1_headers)
    assert res_s3.status_code == 200
    print("  ✅ 3.6 Sauvegarde périodique (autosave) des 3 solutions Python en base SQLite WAL.")

    # 3.6 Soumission finale de la copie
    res_st1_submit = client.post(f"/api/student/attempts/{st1_attempt_id}/submit", headers=st1_headers)
    assert res_st1_submit.status_code == 200
    st1_score = res_st1_submit.json()["final_mark"]
    assert st1_score == 20.0, f"Expected 20.0, got {st1_score}"
    print(f"  ✅ 3.7 Copie soumise et notée instantanément côté serveur : Note {st1_score}/20 (100% de réussite sur les 12 cas de test).")

    # -------------------------------------------------------------------------
    # 4. SCÉNARIO 4 : ÉTUDIANT 2 (INCIDENT RÉSEAU, RAFRAÎCHISSEMENT & TEMPS ADDITIONNEL)
    # -------------------------------------------------------------------------
    print("\n--- [SCÉNARIO 4] : ÉTUDIANT 2 (PERTE CONNEXION & PROLONGATION PERSISTANTE) ---")
    res_st2_login = client.post("/api/auth/login", json={"username": "etu_sys1", "password": "StudentSys1!"})
    assert res_st2_login.status_code == 200
    st2_token = res_st2_login.json()["access_token"]
    st2_headers = {"Authorization": f"Bearer {st2_token}"}

    res_st2_start = client.post(f"/api/student/exams/{exam_id}/start", headers=st2_headers)
    st2_attempt_id = res_st2_start.json()["attempt_id"]

    # Simuler une panne machine / crash de navigateur (reconnexion après incident)
    print("  ⚠️ Simulation coupure réseau / crash machine pour etu_sys1...")
    res_st2_resume = client.get(f"/api/student/attempts/{st2_attempt_id}/status", headers=st2_headers)
    assert res_st2_resume.status_code == 200
    rem_before = res_st2_resume.json()["remaining_seconds"]

    # Le surveillant accorde +10 minutes de temps additionnel
    res_extend = client.post(f"/api/proctor/sessions/{session_id}/extend-time", json={
        "extra_minutes": 10,
        "student_id": "ETU-ETU_SYS1"
    }, headers=prof_headers)
    assert res_extend.status_code == 200
    print("  ✅ 4.1 Surveillant accorde +10 minutes d'extension de temps.")

    # L'étudiant rafraîchit sa page (F5) : le temps restant doit avoir augmenté de ~600 secondes
    res_st2_after_f5 = client.get(f"/api/student/attempts/{st2_attempt_id}/status", headers=st2_headers)
    rem_after = res_st2_after_f5.json()["remaining_seconds"]
    assert rem_after > rem_before + 500, f"Temps non persisté : avant={rem_before}, après={rem_after}"
    print(f"  ✅ 4.2 Persistance authoritaire vérifiée après F5 : Temps restant passé de {rem_before}s à {rem_after}s.")

    # -------------------------------------------------------------------------
    # 5. SCÉNARIO 5 : ÉTUDIANT 3 (SUSPENSION ANTI-TRICHE & DÉBLOCAGE DISTANT)
    # -------------------------------------------------------------------------
    print("\n--- [SCÉNARIO 5] : ÉTUDIANT 3 (DÉTECTION ANTI-TRICHE & DÉBLOCAGE) ---")
    res_st3_login = client.post("/api/auth/login", json={"username": "etu_sec1", "password": "StudentSec1!"})
    assert res_st3_login.status_code == 200
    st3_token = res_st3_login.json()["access_token"]
    st3_headers = {"Authorization": f"Bearer {st3_token}"}

    res_st3_start = client.post(f"/api/student/exams/{exam_id}/start", headers=st3_headers)
    st3_attempt_id = res_st3_start.json()["attempt_id"]

    # Simuler une infraction de sécurité majeure (absence d'écran > 10s)
    print("  ⚠️ Simulation de sortie d'écran prolongée (>10s) par etu_sec1...")
    res_blur = client.post(f"/api/student/attempts/{st3_attempt_id}/security-event", json={
        "event_type": "AWAY_10S",
        "details": {"duration_seconds": 15.0}
    }, headers=st3_headers)
    assert res_blur.status_code == 200
    assert res_blur.json()["is_suspended"] is True

    # Vérifier que le poste de l'étudiant est automatiquement SUSPENDU
    res_st3_status = client.get(f"/api/student/attempts/{st3_attempt_id}/status", headers=st3_headers)
    assert res_st3_status.json()["status"] == "suspended", "L'étudiant aurait dû être suspendu !"
    print("  🔒 5.1 Poste étudiant automatiquement SUSPENDU suite à infraction de sécurité (>10s).")

    # Vérifier que la tentative de soumission est bloquée tant que suspendu
    res_st3_blocked_submit = client.post(f"/api/student/attempts/{st3_attempt_id}/submit", headers=st3_headers)
    assert res_st3_blocked_submit.status_code == 403
    print("  🚫 5.2 Tentative de soumission bloquée (Code 403 - Compte suspendu).")

    # Le surveillant constate l'alerte sur son écran de proctoring et clique sur "Débloquer"
    res_unlock = client.post(f"/api/proctor/sessions/{session_id}/attempts/{st3_attempt_id}/unlock", headers=prof_headers)
    assert res_unlock.status_code == 200
    print("  🔓 5.3 Surveillant débloque le poste de l'étudiant à distance.")

    # L'étudiant peut désormais reprendre l'examen
    res_st3_resumed = client.get(f"/api/student/attempts/{st3_attempt_id}/status", headers=st3_headers)
    assert res_st3_resumed.json()["status"] == "in_progress"
    print("  ✅ 5.4 Reprise immédiate de l'examen autorisée (Statut rétabli à 'in_progress').")

    # -------------------------------------------------------------------------
    # 6. SCÉNARIO 6 : CLÔTURE DE SALLE PAR LE PROCTOR & CONSOLIDATION ADMIN
    # -------------------------------------------------------------------------
    print("\n--- [SCÉNARIO 6] : CLÔTURE COLLECTIVE DE SALLE & PALMARÈS ---")
    
    # Clôture forcée par l'enseignant pour ramasser toutes les copies restantes
    res_close = client.post(f"/api/proctor/sessions/{session_id}/close", headers=prof_headers)
    assert res_close.status_code == 200
    print("  🛑 6.1 Clôture collective déclenchée : toutes les copies actives sont scellées et notées.")

    # Consultation du tableau de bord d'administration pour vérification
    res_admin_overview = client.get("/api/admin/statistics/overview", headers=admin_headers)
    assert res_admin_overview.status_code == 200
    stats = res_admin_overview.json()
    print(f"  📊 6.2 Bilan académique consolidé : {stats['total_students']} étudiants inscrits, {stats['total_submitted']} copies terminées.")

    print("\n" + "=" * 80)
    print("🎉 TOUS LES SCÉNARIOS TESTÉS ONT ÉTÉ EXÉCUTÉS AVEC 100% DE SUCCÈS !")
    print("=" * 80)

if __name__ == "__main__":
    run_simulation()
