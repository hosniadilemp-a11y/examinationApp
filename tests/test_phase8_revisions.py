import json
import pytest

def test_waiting_room_secrecy_and_sync_launch(client, admin_headers, teacher_headers, student_headers):
    """
    REV-25 : Vérifie que tant que la session est en attente (waiting),
    l'étudiant est placé en salle d'attente et ne reçoit AUCUNE question (secret absolu).
    Dès que l'enseignant lance l'épreuve, les questions sont transmises.
    """
    # 1. Création d'un examen et d'une session en attente
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Salle d'Attente", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Python est-il compilé en bytecode ?", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    )

    # Ouverture de session par le surveillant (statut par défaut : waiting)
    sess_res = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-WAIT"}).json()
    session_id = sess_res["session_id"]
    assert sess_res["status"] == "waiting"

    # 2. L'étudiant tente de démarrer : doit recevoir status "waiting" SANS questions
    res_wait = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert res_wait.status_code == 200
    wait_data = res_wait.json()
    assert wait_data["status"] == "waiting"
    assert "questions" not in wait_data
    assert wait_data["attempt_status"] == "waiting"
    assert wait_data["room_id"] == "SALLE-TP-WAIT"

    # 3. Le surveillant lance l'épreuve synchronisée
    res_launch = client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)
    assert res_launch.status_code == 200
    assert res_launch.json()["status"] == "in_progress"

    # 4. L'étudiant réitère : reçoit les questions et le statut in_progress
    res_active = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers)
    assert res_active.status_code == 200
    active_data = res_active.json()
    assert active_data["attempt_status"] == "in_progress"
    assert "questions" in active_data
    assert len(active_data["questions"]) == 1

def test_proctor_close_all_session(client, admin_headers, teacher_headers, student_headers):
    """
    REV-30 : Vérifie la clôture collective de l'épreuve (force-submission de toutes les copies).
    """
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Clôture Collective", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Test ?", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-CLOSE"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    # Démarrage étudiant
    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]

    # Sauvegarde d'une réponse
    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q1["id"], "answer": True})

    # Clôture collective par le surveillant
    res_close = client.post(f"/api/proctor/sessions/{session_id}/close", headers=teacher_headers)
    assert res_close.status_code == 200
    close_data = res_close.json()
    assert close_data["status"] == "completed"
    assert close_data["submitted_count"] >= 1

    # Vérification que la tentative est bien passée en 'submitted'
    status_res = client.get(f"/api/student/attempts/{attempt_id}/status", headers=student_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "submitted"
    assert status_res.json()["final_mark"] == 20.0

def test_unlock_attempt_resets_suspension_count(client, admin_headers, teacher_headers, student_headers):
    """
    REV-29 : Vérifie que le déblocage par le surveillant remet à 0 le compteur de suspensions.
    """
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Test Reset Warning", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TP-WARN"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]

    # Suspension via événement de sécurité
    client.post(
        f"/api/student/attempts/{attempt_id}/security-event",
        headers=student_headers,
        json={"event_type": "AWAY_10S", "details": {"reason": "Sortie d'écran"}}
    )

    overview = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=teacher_headers).json()
    card = next(c for c in overview["student_cards"] if c["attempt_id"] == attempt_id)
    assert card["status"] == "suspended"
    assert card["suspension_count"] >= 1

    # Déblocage par le surveillant
    res_unlock = client.post(f"/api/proctor/sessions/{session_id}/attempts/{attempt_id}/unlock", headers=teacher_headers)
    assert res_unlock.status_code == 200

    # Vérification de la remise à zéro du compteur de suspension
    overview_after = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=teacher_headers).json()
    card_after = next(c for c in overview_after["student_cards"] if c["attempt_id"] == attempt_id)
    assert card_after["status"] == "in_progress"
    assert card_after["suspension_count"] == 0

def test_authoritative_timer_remaining_seconds(client, admin_headers, teacher_headers, student_headers):
    """
    REV-28 : Vérifie que l'auto-sauvegarde calcule et retourne le temps restant exact côté serveur.
    """
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Test Authoritative Timer", "duration_minutes": 45, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Chrono ?", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-TIMER"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]

    res_save = client.post(
        f"/api/student/attempts/{attempt_id}/save-answer",
        headers=student_headers,
        json={"question_id": q1["id"], "answer": True}
    )
    assert res_save.status_code == 200
    save_data = res_save.json()
    assert "remaining_seconds" in save_data
    # 45 minutes = 2700 secondes, doit être autour de 2700
    assert 2690 <= save_data["remaining_seconds"] <= 2700

def test_custom_exam_creation_and_automatic_session(client, admin_headers, teacher_headers):
    """
    REV-31 : Vérifie la création d'un examen sur-mesure avec room_id,
    copie automatique des questions modèles et initialisation de la session en attente.
    """
    payload = {
        "title": "Examen Custom Crypto Réseau",
        "module_code": "CRYPTO",
        "duration_minutes": 45,
        "global_points": 20.0,
        "room_id": "SALLE-TP-CUSTOM",
        "instructions": "Épreuve officielle sur poste individuel.",
        "group_ids": ["CYBER-SEC"],
        "shuffle_questions": True,
        "shuffle_options": True
    }
    res = client.post("/api/exams", headers=admin_headers, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Examen Custom Crypto Réseau"
    assert data["module_code"] == "CRYPTO"
    assert data["question_count"] >= 5
    assert "CYBER-SEC" in data["assigned_groups"]

    # Vérifier que la session a été créée en attente pour la salle
    sess_res = client.get("/api/proctor/sessions?room_id=SALLE-TP-CUSTOM", headers=teacher_headers)
    assert sess_res.status_code == 200
    sessions = sess_res.json()
    assert len(sessions) >= 1
    assert any(s["exam_id"] == data["id"] and s["status"] == "waiting" for s in sessions)

def test_student_dashboard_submitted_status_and_card_display(client, admin_headers, teacher_headers, student_headers):
    """
    REV-33 : Vérifie que l'API /api/student/exams/available retourne le statut 'submitted' et la note finale /20.
    """
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "PYTHON_INIT", "title": "Examen Test Card Soumis", "duration_minutes": 30, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]

    q1 = client.post(
        f"/api/exams/{exam_id}/questions",
        headers=admin_headers,
        json={"ordering": 1, "type": "boolean", "prompt_markdown": "Test ?", "points": 20.0, "options_json": "[]", "correct_answers_json": json.dumps(True)}
    ).json()

    session_id = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-CARD"}).json()["session_id"]
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)

    start_data = client.post(f"/api/student/exams/{exam_id}/start", headers=student_headers).json()
    attempt_id = start_data["attempt_id"]

    client.post(f"/api/student/attempts/{attempt_id}/save-answer", headers=student_headers, json={"question_id": q1["id"], "answer": True})
    client.post(f"/api/student/attempts/{attempt_id}/submit", headers=student_headers)

    # Récupération de la liste des examens pour l'étudiant
    res_avail = client.get("/api/student/exams/available", headers=student_headers)
    assert res_avail.status_code == 200
    avail_list = res_avail.json()
    target_card = next(c for c in avail_list if c["exam_id"] == exam_id)
    assert target_card["attempt_status"] == "submitted"
    assert target_card["final_mark"] == 20.0

def test_waiting_room_fullscreen_and_dashboard_navigation_contract():
    """
    REV-34, REV-35, REV-36 : Vérifie l'intégration du plein écran de la salle d'attente,
    de l'alerte/confirmation de sortie, et de la méthode renderStudentDashboard.
    """
    import os
    app_js_path = os.path.join("frontend", "js", "app.js")
    anticheat_js_path = os.path.join("frontend", "js", "anticheat.js")
    index_html_path = os.path.join("frontend", "index.html")

    with open(app_js_path, "r", encoding="utf-8") as f:
        app_js = f.read()

    with open(anticheat_js_path, "r", encoding="utf-8") as f:
        anticheat_js = f.read()

    with open(index_html_path, "r", encoding="utf-8") as f:
        index_html = f.read()

    # REV-36 : La méthode renderStudentDashboard doit être définie sur le contrôleur
    assert "renderStudentDashboard()" in app_js, "renderStudentDashboard doit être défini dans app.js"

    # REV-34 : Mode plein écran requis dans la salle d'attente et flou en cas de sortie
    assert "view-waiting-room" in index_html, "La vue view-waiting-room doit exister dans index.html"
    assert "_handleWaitingRoomFullscreenChange" in app_js, "_handleWaitingRoomFullscreenChange doit être présent dans app.js"
    assert "view-waiting-room" in anticheat_js, "anticheat.js doit couvrir view-waiting-room pour le flou et le déflou"

    # REV-35 : Confirmation et alerte lors de l'abandon de la salle d'attente
    assert "btn-waiting-room-leave" in app_js, "btn-waiting-room-leave doit être géré dans app.js"
    assert "confirm(" in app_js, "Un dialogue de confirmation doit prévenir l'étudiant avant de quitter la salle d'attente"
    assert "exitFullscreen" in app_js, "La sortie propre du plein écran doit être déclenchée lors de la confirmation d'abandon"

def test_proctor_countdown_timer_authoritative_clock(client, admin_headers, teacher_headers):
    """
    REV-37 : Surveillance temps réel — Vérifie que l'API de proctoring fournit le chronomètre
    authoritative session_remaining_seconds et que le widget HTML et le ticker JS sont présents.
    """
    import os
    index_html_path = os.path.join("frontend", "index.html")
    app_js_path = os.path.join("frontend", "js", "app.js")
    with open(index_html_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "proctor-session-timer" in html, "Le widget #proctor-session-timer doit être présent dans le header de surveillance"
    assert "_updateProctorTimerDisplay" in js, "Le contrôleur JS doit mettre à jour le chronomètre de session"
    assert "proctorTimerInterval" in js, "Un timer 1s doit décrémenter le chronomètre de surveillance"

    # Vérification API
    res_exam = client.post(
        "/api/exams",
        headers=admin_headers,
        json={"module_code": "CRYPTO", "title": "Examen Proctor Clock Test", "duration_minutes": 45, "group_ids": ["GRP-1"]}
    )
    exam_id = res_exam.json()["id"]
    sess_res = client.post("/api/proctor/sessions", headers=teacher_headers, json={"exam_id": exam_id, "room_id": "SALLE-CLOCK"})
    session_id = sess_res.json()["session_id"]

    # Avant lancement: statut waiting
    overview_before = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=teacher_headers).json()
    assert overview_before["status"] == "waiting"

    # Lancement de la session
    client.post(f"/api/proctor/sessions/{session_id}/launch", headers=teacher_headers)
    overview_after = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=teacher_headers).json()
    assert overview_after["status"] == "in_progress"
    assert "session_remaining_seconds" in overview_after
    assert overview_after["session_remaining_seconds"] is not None
    assert 0 < overview_after["session_remaining_seconds"] <= 45 * 60

def test_removal_of_voir_statistiques_everywhere():
    """
    REV-38 : Épuration UI — Vérifie que le bouton 'Voir Statistiques' a été supprimé
    partout (Dashboard, Score, Navigation).
    """
    import os
    index_html_path = os.path.join("frontend", "index.html")
    app_js_path = os.path.join("frontend", "js", "app.js")
    with open(index_html_path, "r", encoding="utf-8") as f:
        html = f.read()
    with open(app_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    # Dans index.html
    assert 'id="btn-open-full-stats"' not in html, "Le bouton #btn-open-full-stats doit être supprimé du Dashboard"
    assert 'id="btn-score-view-stats"' not in html, "Le bouton #btn-score-view-stats doit être supprimé de la vue Score"

    # Dans la nav étudiante de app.js
    assert "nav-stats" not in js, "Le bouton de navigation nav-stats doit être retiré du menu étudiant"

def test_super_admin_statistics_overview_and_results(client, admin_headers, student_headers):
    """
    REV-39 & REV-40 : Vérifie l'API d'aperçu statistique global et le listing des résultats.
    """
    res_overview = client.get("/api/admin/statistics/overview", headers=admin_headers)
    assert res_overview.status_code == 200
    ov = res_overview.json()
    assert "total_students" in ov
    assert "total_teachers" in ov
    assert "total_modules" in ov
    assert "total_exams" in ov
    assert "average_mark" in ov
    assert "pass_rate" in ov
    assert "recent_submissions" in ov
    assert "groups_summary" in ov

    # Restriction: un étudiant ne peut pas accéder à l'aperçu admin
    res_forbidden = client.get("/api/admin/statistics/overview", headers=student_headers)
    assert res_forbidden.status_code == 403

    # Listing filtré des résultats
    res_results = client.get("/api/admin/results", headers=admin_headers)
    assert res_results.status_code == 200
    assert isinstance(res_results.json(), list)

def test_super_admin_csv_import_and_export_multi_salles(client, admin_headers):
    """
    REV-40 : Ingestion de fichier CSV de résultats provenant d'une autre salle et export consolidé.
    """
    csv_content = (
        "student_id;username;full_name;group_id;room_id;raw_score;final_mark;status\n"
        "ETU-SALLE-B-01;etu_b1;Brahim Salle B;GRP-2;SALLE-B;17.5;17.5;submitted\n"
        "ETU-SALLE-B-02;etu_b2;Chadia Salle B;GRP-2;SALLE-B;14.0;14.0;submitted\n"
    )

    files = {"file": ("student_submissions.csv", csv_content.encode("utf-8"), "text/csv")}
    res_import = client.post("/api/admin/csv/import/results", headers=admin_headers, files=files)
    assert res_import.status_code == 200
    import_data = res_import.json()
    assert import_data["success"] is True
    assert import_data["imported_count"] >= 2

    # Vérification que l'étudiant importé figure dans les résultats
    res_results = client.get("/api/admin/results?room_id=SALLE-B", headers=admin_headers)
    assert res_results.status_code == 200
    results = res_results.json()
    assert any(r["student_id"] == "ETU-SALLE-B-01" and r["final_mark"] == 17.5 for r in results)

    # Exportation CSV globale des résultats
    res_export = client.get("/api/admin/csv/export/exam-results", headers=admin_headers)
    assert res_export.status_code == 200
    assert "text/csv" in res_export.headers.get("content-type", "")
    assert "resultats_examens_officiels.csv" in res_export.headers.get("content-disposition", "")

def test_student_clear_password_crud(client, admin_headers):
    """
    REV-43 : Vérifie que le mot de passe est visible en clair et modifiable dans le CRUD étudiant.
    """
    # 1. Création avec mot de passe en clair explicite
    res_create = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "id": "ETU-PWD-TEST",
            "username": "etu_pwd_test",
            "full_name": "Étudiant Test Pwd",
            "role": "student",
            "group_id": "DEV-IA",
            "password": "ClearPass123!"
        }
    )
    assert res_create.status_code == 201
    user_data = res_create.json()
    assert user_data["plain_password"] == "ClearPass123!"

    # 2. Consultation
    res_get = client.get(f"/api/users/{user_data['id']}", headers=admin_headers)
    assert res_get.status_code == 200
    assert res_get.json()["plain_password"] == "ClearPass123!"

    # 3. Mise à jour du mot de passe
    res_update = client.put(
        f"/api/users/{user_data['id']}",
        headers=admin_headers,
        json={
            "password": "UpdatedClearPass456!"
        }
    )
    assert res_update.status_code == 200
    assert res_update.json()["plain_password"] == "UpdatedClearPass456!"

def test_student_csv_import_with_speciality_and_password(client, admin_headers):
    """
    REV-43 : Vérifie l'importation CSV d'étudiants avec mot de passe et spécialité.
    """
    csv_content = (
        "student_id;username;full_name;specialite;password\n"
        "ETU-CSV-DEV1;etu_csv_dev1;Jean Claude Dev;DEV-IA;MyDevPass2026!\n"
    )
    files = {"file": ("students_import.csv", csv_content.encode("utf-8"), "text/csv")}
    res_import = client.post("/api/admin/csv/import/students", headers=admin_headers, files=files)
    assert res_import.status_code == 200
    assert res_import.json()["success"] is True

    # Vérification des données importées
    res_stu = client.get("/api/users/ETU-CSV-DEV1", headers=admin_headers)
    assert res_stu.status_code == 200
    data = res_stu.json()
    assert data["plain_password"] == "MyDevPass2026!"
    assert data["group_id"] == "DEV-IA"

def test_bulletins_and_realistic_seeded_scores(client, admin_headers, student_headers, db_session):
    """
    REV-44, REV-45, REV-46 : Vérifie la gestion des bulletins, le calcul des moyennes (piliers + examens),
    les verdicts académiques (ADMIS vs AJOURNÉ) et les exports CSV.
    """
    from backend.app.main import _seed_realistic_bulletin_data
    from backend.app.models import Module
    for code, title in [("ALGO", "Algorithmique Fondamentale"), ("LINUX_ADMIN", "Administration Système Linux")]:
        if not db_session.query(Module).filter(Module.code == code).first():
            db_session.add(Module(code=code, title=title))
    db_session.commit()
    _seed_realistic_bulletin_data(db_session)

    # 1. Liste des bulletins
    res = client.get("/api/admin/bulletins", headers=admin_headers)
    assert res.status_code == 200
    bulletins = res.json()
    assert len(bulletins) >= 12

    # Vérification pour un étudiant brillant (etu_dev1)
    b_dev1 = next(b for b in bulletins if b["username"] == "etu_dev1")
    assert b_dev1["speciality"] == "DEV-IA"
    assert b_dev1["plain_password"] == "StudentDev1!"
    f1 = b_dev1["fundamentals"]
    assert f1["ALGO"]["score"] == 16.5
    assert f1["PYTHON_INIT"]["score"] == 18.0
    assert f1["CRYPTO"]["score"] == 14.0
    assert f1["LINUX_ADMIN"]["score"] == 15.0
    assert b_dev1["exams"]["theoretical"]["score"] == 17.5
    assert b_dev1["exams"]["practical"]["score"] == 18.0
    assert b_dev1["general_average"] >= 10.0
    assert b_dev1["is_pass"] is True
    assert b_dev1["verdict"] == "ADMIS"

    # Vérification pour un étudiant ajourné (etu_dev4)
    b_dev4 = next(b for b in bulletins if b["username"] == "etu_dev4")
    assert b_dev4["general_average"] < 10.0
    assert b_dev4["is_pass"] is False
    assert b_dev4["verdict"] == "AJOURNÉ"

    # 2. Consultation individuelle d'un bulletin par l'admin
    res_single = client.get(f"/api/admin/bulletins/{b_dev1['student_id']}", headers=admin_headers)
    assert res_single.status_code == 200
    assert res_single.json()["student_id"] == b_dev1["student_id"]

    # 3. Export CSV consolidé des bulletins
    res_csv = client.get("/api/admin/bulletins/export-csv", headers=admin_headers)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")
    assert "bulletins_academiques_consolides.csv" in res_csv.headers.get("content-disposition", "")
    csv_text = res_csv.text
    assert "Matricule" in csv_text
    assert "Decision Jury" in csv_text
    assert "etu_dev1" in csv_text
    assert "ADMIS" in csv_text

    # 4. Consultation de son propre bulletin par l'étudiant
    res_my_b = client.get("/api/student/bulletin", headers=student_headers)
    assert res_my_b.status_code == 200
    assert "fundamentals" in res_my_b.json()
    assert "exams" in res_my_b.json()

def test_bulletin_and_palmares_pdf_docx_zip_exports(client, admin_headers, student_headers, db_session):
    """
    REV-47 : Vérifie l'exportation des bulletins individuels et groupés en PDF,
    Word (.docx) et archive ZIP, ainsi que le palmarès officiel de spécialité trié par module.
    """
    from backend.app.main import _seed_realistic_bulletin_data
    from backend.app.models import Module
    import zipfile
    import io

    for code, title in [("ALGO", "Algorithmique Fondamentale"), ("LINUX_ADMIN", "Administration Système Linux")]:
        if not db_session.query(Module).filter(Module.code == code).first():
            db_session.add(Module(code=code, title=title))
    db_session.commit()
    _seed_realistic_bulletin_data(db_session)

    # 1. Export individuel PDF admin
    res_pdf = client.get("/api/admin/bulletins/ETU-ETU_DEV1/export-pdf", headers=admin_headers)
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000

    # 2. Export individuel DOCX admin
    res_docx = client.get("/api/admin/bulletins/ETU-ETU_DEV1/export-docx", headers=admin_headers)
    assert res_docx.status_code == 200
    assert "wordprocessingml.document" in res_docx.headers["content-type"]
    assert len(res_docx.content) > 10000

    # 3. Export ZIP des bulletins en PDF
    res_zip_pdf = client.get("/api/admin/bulletins/export-zip?format=pdf&speciality=DEV-IA", headers=admin_headers)
    assert res_zip_pdf.status_code == 200
    assert res_zip_pdf.headers["content-type"] == "application/zip"
    zf_pdf = zipfile.ZipFile(io.BytesIO(res_zip_pdf.content))
    pdf_names = zf_pdf.namelist()
    assert any("ETU-ETU_DEV1" in name for name in pdf_names)
    assert any(name.endswith(".pdf") for name in pdf_names)
    assert "RECAPITULATIF_PALMARES.csv" in pdf_names

    # 4. Export ZIP des bulletins en DOCX
    res_zip_docx = client.get("/api/admin/bulletins/export-zip?format=docx&speciality=DEV-IA", headers=admin_headers)
    assert res_zip_docx.status_code == 200
    assert res_zip_docx.headers["content-type"] == "application/zip"
    zf_docx = zipfile.ZipFile(io.BytesIO(res_zip_docx.content))
    docx_names = zf_docx.namelist()
    assert any(name.endswith(".docx") for name in docx_names)

    # 5. Export Palmarès Spécialité trié par module (PDF Paysage)
    res_palmares_pdf = client.get("/api/admin/results/export-pdf?speciality=DEV-IA&sort_by_module=PYTHON_INIT", headers=admin_headers)
    assert res_palmares_pdf.status_code == 200
    assert res_palmares_pdf.headers["content-type"] == "application/pdf"
    assert len(res_palmares_pdf.content) > 1000

    # 6. Export Palmarès Spécialité trié par module (Word DOCX Paysage)
    res_palmares_docx = client.get("/api/admin/results/export-docx?speciality=DEV-IA&sort_by_module=PYTHON_INIT", headers=admin_headers)
    assert res_palmares_docx.status_code == 200
    assert "wordprocessingml.document" in res_palmares_docx.headers["content-type"]
    assert len(res_palmares_docx.content) > 10000

    # 7. Téléchargement de son bulletin en PDF par l'étudiant
    res_my_pdf = client.get("/api/student/bulletin/export-pdf", headers=student_headers)
    assert res_my_pdf.status_code == 200
    assert res_my_pdf.headers["content-type"] == "application/pdf"
    assert len(res_my_pdf.content) > 1000

    # 8. Téléchargement de son bulletin en DOCX par l'étudiant
    res_my_docx = client.get("/api/student/bulletin/export-docx", headers=student_headers)
    assert res_my_docx.status_code == 200
    assert "wordprocessingml.document" in res_my_docx.headers["content-type"]
    assert len(res_my_docx.content) > 10000






