"""
Tests de validation de la configuration de pré-déploiement et des 11 chantiers :
- Purge et initialisation des 3 modules (PYTHON_INIT, CRYPTO, LINUX_ADMIN) avec leurs enseignants dédiés.
- 4 classes (DEV-IA, SYS-ADMIN, CYBER-SEC, GRP-1) de 4 étudiants chacune (16 étudiants au total).
- Examens modèles pour les 3 modules (40 QCM pour Python Théorique -> 20 aléatoires par étudiant).
- Isolation des examens par enseignant.
- Import CSV Étudiants (ID;nom;prenom;annee;specialite) et Enseignants (nom;prenom;email;modules) avec génération automatique de login et mot de passe.
- Modification du login (username) et mot de passe par l'Admin.
- Horloge serveur synchronisée (server_time_hms, server_epoch_ms).
- Analyse Psychométrique (avec 0 copie et après soumission de copies).
- Téléchargement des notes finales de tous les étudiants à chaque examen (JSON, CSV, PDF).
"""
import io
from scripts.reset_and_seed_exact_3_exams import reset_and_seed_3_exams
from backend.app.models import User, Group, Module, Exam


def test_deployment_seeding_4_classes_3_modules_and_exam_grade_downloads(client, admin_headers, teacher_headers, db_session):
    reset_and_seed_3_exams(db_session, clear_practice=True)

    # 1. Vérification des 3 modules et de leurs enseignants dédiés
    for m_code, t_username in [
        ("PYTHON_INIT", "prof_python"),
        ("CRYPTO", "prof_crypto"),
        ("LINUX_ADMIN", "prof_linux"),
    ]:
        mod = db_session.query(Module).filter(Module.code == m_code).first()
        assert mod is not None
        t_user = db_session.query(User).filter(User.username == t_username).first()
        assert t_user is not None
        assert t_user.role == "teacher"
        assert any(m.code == m_code for m in t_user.assigned_modules)

    # 2. Vérification des 4 classes avec 4 étudiants chacune (16 étudiants)
    expected_classes = ["DEV-IA", "SYS-ADMIN", "CYBER-SEC", "GRP-1"]
    for gid in expected_classes:
        grp = db_session.query(Group).filter(Group.id == gid).first()
        assert grp is not None
        students_in_class = db_session.query(User).filter(User.role == "student", User.group_id == gid).all()
        assert len(students_in_class) == 4, f"La classe {gid} doit contenir exactement 4 étudiants"
        for s in students_in_class:
            assert s.full_name
            assert s.email
            assert s.plain_password
            assert s.enrollment_year == "2025-2026"

    # 3. Vérification des examens modèles pour les 3 modules
    for ex_id, mod_code, expected_q_count in [
        ("EXAM-THEO-PYTHON", "PYTHON_INIT", 40),
        ("EXAM-PRAC-PYTHON", "PYTHON_INIT", 5),
        ("EXAM-THEO-CRYPTO", "CRYPTO", 5),
        ("EXAM-THEO-LINUX", "LINUX_ADMIN", 5),
    ]:
        ex = db_session.query(Exam).filter(Exam.id == ex_id).first()
        assert ex is not None
        assert ex.module_code == mod_code
        assert len(ex.questions) == expected_q_count
        assert ex.shuffle_questions is True
        assert ex.shuffle_options is True

        # 4. Vérification du téléchargement des notes finales (JSON, CSV, PDF) pour chaque examen
        res_json = client.get(f"/api/exams/{ex_id}/results", headers=teacher_headers)
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["exam_id"] == ex_id
        assert data["total_students"] == 16
        assert len(data["students"]) == 16

        res_csv = client.get(f"/api/exams/{ex_id}/results/export-csv", headers=teacher_headers)
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "Note Finale (/20)" in res_csv.text
        assert "etu_dev1" in res_csv.text
        assert "etu_log4" in res_csv.text

        res_pdf = client.get(f"/api/exams/{ex_id}/results/export-pdf", headers=admin_headers)
        assert res_pdf.status_code == 200
        assert res_pdf.headers["content-type"] == "application/pdf"
        assert res_pdf.content.startswith(b"%PDF")


def test_psychometric_analysis_40_to_20_random_clock_and_csv_autogeneration(client, admin_headers, db_session):
    reset_and_seed_3_exams(db_session, clear_practice=True)

    # 1. Analyse Psychométrique à vide (0 candidat soumis) -> aucun champ manquant (pas de NaN%)
    res_empty = client.get("/api/exams/EXAM-THEO-PYTHON/item-analysis", headers=admin_headers)
    assert res_empty.status_code == 200
    empty_data = res_empty.json()
    assert empty_data["total_candidates"] == 0
    assert len(empty_data["questions_analysis"]) == 40
    for q_stat in empty_data["questions_analysis"]:
        assert "p_upper" in q_stat and q_stat["p_upper"] == 0.0
        assert "p_lower" in q_stat and q_stat["p_lower"] == 0.0
        assert "avg_awarded_points" in q_stat
        assert "quality_badge" in q_stat

    # 2. Ouverture et lancement de la session de surveillance pour EXAM-THEO-PYTHON
    open_res = client.post("/api/proctor/sessions", json={"exam_id": "EXAM-THEO-PYTHON", "room_id": "SALLE-TP-1"}, headers=admin_headers)
    assert open_res.status_code == 200
    session_id = open_res.json()["session_id"]

    launch_res = client.post(f"/api/proctor/sessions/{session_id}/launch", headers=admin_headers)
    assert launch_res.status_code == 200

    # Vérifier l'horloge serveur dans l'aperçu proctor
    overview_res = client.get(f"/api/proctor/sessions/{session_id}/overview", headers=admin_headers)
    assert overview_res.status_code == 200
    ov = overview_res.json()
    assert "server_time_hms" in ov
    assert "server_epoch_ms" in ov

    # 3. Connexion de 2 étudiants : chacun reçoit 20 questions aléatoires parmi les 40 + horloge serveur
    login1 = client.post("/api/auth/login", json={"username": "etu_dev1", "password": "StudentDev1!"})
    assert login1.status_code == 200
    h1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

    login2 = client.post("/api/auth/login", json={"username": "etu_dev2", "password": "StudentDev2!"})
    assert login2.status_code == 200
    h2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    start1 = client.post("/api/student/exams/EXAM-THEO-PYTHON/start", headers=h1)
    assert start1.status_code == 200
    d1 = start1.json()
    assert len(d1["questions"]) == 20
    assert "server_time_hms" in d1
    assert "server_epoch_ms" in d1

    start2 = client.post("/api/student/exams/EXAM-THEO-PYTHON/start", headers=h2)
    assert start2.status_code == 200
    d2 = start2.json()
    assert len(d2["questions"]) == 20

    # Soumission des 2 copies et vérification de l'Analyse Psychométrique en direct
    client.post(f"/api/student/attempts/{d1['attempt_id']}/submit", headers=h1)
    client.post(f"/api/student/attempts/{d2['attempt_id']}/submit", headers=h2)

    sess_analysis = client.get(f"/api/proctor/sessions/{session_id}/item-analysis", headers=admin_headers)
    assert sess_analysis.status_code == 200
    sa_data = sess_analysis.json()
    assert sa_data["total_candidates"] == 2
    assert len(sa_data["questions_analysis"]) == 40

    # 4. Import CSV Étudiants (ID;nom;prenom;annee;specialite) sans login/mot de passe
    csv_students = "ID;nom;prenom;annee;specialite\nETU-AUTO-99;Zouiten;Nabil;2025-2026;DEV-IA\n"
    res_stu_csv = client.post(
        "/api/admin/csv/import/students",
        files={"file": ("etudiants.csv", io.BytesIO(csv_students.encode("utf-8")), "text/csv")},
        headers=admin_headers,
    )
    assert res_stu_csv.status_code == 200
    assert res_stu_csv.json()["imported_count"] == 1
    auto_stu = db_session.query(User).filter(User.id == "ETU-AUTO-99").first()
    assert auto_stu is not None
    assert auto_stu.username
    assert auto_stu.plain_password

    # 5. Import CSV Enseignants (nom;prenom;email;modules) sans ID/login/mot de passe
    csv_teachers = "nom;prenom;email;modules\nBennani;Sonia;s.bennani@ecole.fr;PYTHON_INIT,CRYPTO\n"
    res_tea_csv = client.post(
        "/api/admin/csv/import/teachers",
        files={"file": ("enseignants.csv", io.BytesIO(csv_teachers.encode("utf-8")), "text/csv")},
        headers=admin_headers,
    )
    assert res_tea_csv.status_code == 200
    assert res_tea_csv.json()["imported_count"] == 1
    auto_tea = db_session.query(User).filter(User.email == "s.bennani@ecole.fr").first()
    assert auto_tea is not None
    assert auto_tea.id.startswith(("TCH-", "ENS-"))
    assert auto_tea.username
    assert auto_tea.plain_password

    # 6. Modification du login (username) et mot de passe par l'Admin
    upd_res = client.put(
        f"/api/users/{auto_stu.id}",
        json={"username": "nabil.zouiten.custom", "password": "NewPass@2026"},
        headers=admin_headers,
    )
    assert upd_res.status_code == 200
    assert upd_res.json()["username"] == "nabil.zouiten.custom"
    assert upd_res.json()["plain_password"] == "NewPass@2026"
