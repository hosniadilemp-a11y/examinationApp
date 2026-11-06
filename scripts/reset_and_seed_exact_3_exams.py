"""
Script officiel d'initialisation et de pré-déploiement de la base de données :
1. Purge intégrale de tous les anciens examens, sessions, tentatives, questions et modules parasites.
2. Insertion de l'Administrateur (`admin`) et des Enseignants dédiés aux 3 modules de test :
   - `PYTHON_INIT` (Programmation Python) -> `prof_python` (+ `prof_martin`)
   - `CRYPTO` (Cryptographie & Sécurité) -> `prof_crypto` (+ `prof_martin`)
   - `LINUX_ADMIN` (Administration Système Linux) -> `prof_linux` (+ `prof_martin`)
3. Insertion de 4 Spécialités / Classes (Groupes), chacune composée de 4 étudiants complets (16 étudiants au total) :
   - `DEV-IA` (4 étudiants : `etu_dev1` à `etu_dev4`)
   - `SYS-ADMIN` (4 étudiants : `etu_sys1` à `etu_sys4`)
   - `CYBER-SEC` (4 étudiants : `etu_sec1` à `etu_sec4`)
   - `GRP-1` (4 étudiants : `etudiant1`, `etu_log2`, `etu_log3`, `etu_log4`)
4. Création des Examens Modèles pour les 3 modules (`PYTHON_INIT`, `CRYPTO`, `LINUX_ADMIN`) :
   - `EXAM-THEO-PYTHON` : Banque de 40 questions théoriques, tirage aléatoire de 20 questions par étudiant, mélange intégral des questions et des choix.
   - `EXAM-PRAC-PYTHON` : 5 défis algorithmiques pratiques Python.
   - `EXAM-THEO-CRYPTO` : Épreuve théorique Cryptographie & Sécurité (questions et choix mélangés).
   - `EXAM-THEO-LINUX` : Épreuve théorique Administration Système Linux (questions et choix mélangés).
"""
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, Base, engine
from backend.app.models import (
    User, Module, Group, Exam, Question, ExamSession,
    StudentAttempt, StudentAnswer, AuditLog,
    PracticeAttempt, TrainingAttempt, ChapterProgress,
    exam_groups, teacher_modules
)
from backend.app.security import hash_password
from backend.app.services.python_exam_generator import normalize_curriculum_question


def _load_extra_35_python_mcqs():
    """Extrait 35 questions officielles depuis curriculum.json pour compléter EXAM-THEO-PYTHON à 40 questions,
    en respectant fidèlement leurs types (mcq, intruder, yesno, simple_blank, matching)."""
    curriculum_path = os.path.join(
        os.path.dirname(__file__), "..", "backend", "app", "data", "python_training", "curriculum.json"
    )
    extracted = []
    if os.path.exists(curriculum_path):
        with open(curriculum_path, "r", encoding="utf-8") as f:
            curr = json.load(f)
        exam_marked = []
        others = []
        for ch in curr.get("chapters", []):
            for q in ch.get("mcq_questions", []):
                if q.get("Exams") or q.get("is_exam"):
                    exam_marked.append(q)
                else:
                    others.append(q)
        pool = exam_marked + others
        for i, q in enumerate(pool[:35], start=6):
            norm = normalize_curriculum_question(q, idx=i)
            extracted.append(norm)
    while len(extracted) < 35:
        idx = len(extracted) + 6
        extracted.append({
            "type": "single_choice",
            "prompt_markdown": f"En Python, quelle est la valeur de `len(range({idx}))` ?",
            "options": [str(idx), str(idx - 1), str(idx + 1), "0"],
            "correct_answers": 0,
            "negative_penalty": 0.0
        })
    return extracted[:35]


def _load_40_crypto_questions():
    """Charge 40 questions théoriques de Cryptographie & Sécurité avec barème unitaire (1.0 pt)."""
    questions = []
    seen = set()
    base_5 = [
        {
            "type": "single_choice",
            "prompt_markdown": "Quelle est la taille du condensat (hash) produit par l'algorithme **SHA-256** ?",
            "points": 1.0,
            "options": ["128 bits", "160 bits", "256 bits (32 octets)", "512 bits"],
            "correct_answers": 2
        },
        {
            "type": "multi_choice",
            "prompt_markdown": "Parmi les algorithmes suivants, lesquels sont des algorithmes de chiffrement **asymétrique** ? *(Plusieurs réponses)*",
            "points": 1.0,
            "options": ["RSA", "AES-GCM", "ECC (Courbes Elliptiques)", "ChaCha20", "ElGamal"],
            "correct_answers": [0, 2, 4]
        },
        {
            "type": "boolean",
            "prompt_markdown": "En cryptographie asymétrique, la signature numérique d'un message est générée à l'aide de la **clé privée** de l'expéditeur et vérifiée avec sa **clé publique**.",
            "points": 1.0,
            "options": [],
            "correct_answers": True
        },
        {
            "type": "fill_blank",
            "prompt_markdown": "Quel standard de chiffrement symétrique par blocs (successeur de DES, blocs de 128 bits) est aujourd'hui le standard mondial du NIST ? `_____`",
            "points": 1.0,
            "options": [],
            "correct_answers": ["AES", "Rijndael"]
        },
        {
            "type": "matching",
            "prompt_markdown": "Associez chaque concept cryptographique à la propriété de sécurité qu'il garantit principalement :",
            "points": 1.0,
            "options": [
                {"left": "Chiffrement AES-256", "right": "Confidentialité des données"},
                {"left": "Fonction de hachage SHA-256", "right": "Intégrité des données"},
                {"left": "Signature numérique RSA / ECDSA", "right": "Authenticité et non-répudiation"}
            ],
            "correct_answers": {
                "Chiffrement AES-256": "Confidentialité des données",
                "Fonction de hachage SHA-256": "Intégrité des données",
                "Signature numérique RSA / ECDSA": "Authenticité et non-répudiation"
            }
        }
    ]
    for q in base_5:
        seen.add(q["prompt_markdown"].strip())
        questions.append(q)

    seeds_path = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "seeds", "seed_crypto_30.json")
    if os.path.exists(seeds_path):
        with open(seeds_path, "r", encoding="utf-8") as f:
            data_30 = json.load(f)
        for item in data_30:
            prompt = item.get("prompt_markdown", "").strip()
            if prompt and prompt not in seen:
                seen.add(prompt)
                opts = item.get("options_json", [])
                if isinstance(opts, str):
                    try: opts = json.loads(opts)
                    except Exception: pass
                corr = item.get("correct_answers_json", None)
                if isinstance(corr, str):
                    try: corr = json.loads(corr)
                    except Exception: pass
                questions.append({
                    "type": item.get("type", "single_choice"),
                    "prompt_markdown": prompt,
                    "points": 1.0,
                    "options": opts,
                    "correct_answers": corr
                })

    tpl_path = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "seeds", "templates", "template_exam_crypto.json")
    if os.path.exists(tpl_path) and len(questions) < 40:
        with open(tpl_path, "r", encoding="utf-8") as f:
            tpl_data = json.load(f)
        for item in tpl_data.get("questions", []):
            prompt = item.get("prompt_markdown", "").strip()
            if prompt and prompt not in seen:
                seen.add(prompt)
                opts = item.get("options_json", [])
                if isinstance(opts, str):
                    try: opts = json.loads(opts)
                    except Exception: pass
                corr = item.get("correct_answers_json", None)
                if isinstance(corr, str):
                    try: corr = json.loads(corr)
                    except Exception: pass
                questions.append({
                    "type": item.get("type", "single_choice"),
                    "prompt_markdown": prompt,
                    "points": 1.0,
                    "options": opts,
                    "correct_answers": corr
                })

    extra_questions = [
        {
            "type": "single_choice",
            "prompt_markdown": "Quel mode d'opération d'un chiffrement par blocs permet de transformer un algorithme comme AES en chiffrement par flux avec authentification intégrée (AEAD) ?",
            "points": 1.0,
            "options": ["ECB (Electronic Codebook)", "CBC (Cipher Block Chaining)", "GCM (Galois/Counter Mode)", "OFB (Output Feedback)"],
            "correct_answers": 2
        },
        {
            "type": "boolean",
            "prompt_markdown": "L'attaque par Rainbow Tables repose sur un compromis temps-mémoire (time-memory trade-off) visant à inverser des fonctions de hachage dépourvues de sel cryptographique.",
            "points": 1.0,
            "options": [],
            "correct_answers": True
        },
        {
            "type": "single_choice",
            "prompt_markdown": "Quelle fonction de dérivation de clé (KDF) résistante aux attaques matérielles par GPU/ASIC utilise un coût mémoire intensif (memory-hard) ?",
            "points": 1.0,
            "options": ["MD5", "Argon2", "SHA-1", "CRC32"],
            "correct_answers": 1
        },
        {
            "type": "fill_blank",
            "prompt_markdown": "Quel protocole cryptographique permet à deux interlocuteurs d'établir une clé secrète partagée sur un canal de communication non sécurisé sans transmettre la clé elle-même ? `_____`",
            "points": 1.0,
            "options": [],
            "correct_answers": ["Diffie-Hellman", "ECDH", "DH"]
        },
        {
            "type": "multi_choice",
            "prompt_markdown": "Quelles propriétés caractérisent une fonction de hachage cryptographique robuste ? *(Plusieurs réponses)*",
            "points": 1.0,
            "options": ["Résistance aux collisions", "Réversibilité mathématique simple", "Résistance à la seconde préimage", "Effet avalanche (avalanche effect)"],
            "correct_answers": [0, 2, 3]
        }
    ]
    for q in extra_questions:
        if len(questions) >= 40:
            break
        prompt = q["prompt_markdown"].strip()
        if prompt not in seen:
            seen.add(prompt)
            questions.append(q)

    return questions[:40]


def _load_40_linux_questions():
    """Charge 40 questions théoriques variées pour EXAM-THEO-LINUX à partir du curriculum Linux officiel."""
    questions = []
    seen = set()
    base_5 = [
        {
            "type": "single_choice",
            "prompt_markdown": "Sous Linux, quelle valeur octale passée à la commande `chmod` accorde les droits `rwxr-x---` (Propriétaire : lecture/écriture/exécution, Groupe : lecture/exécution, Autres : aucun droit) ?",
            "points": 1.0,
            "options": ["750", "755", "640", "700"],
            "correct_answers": 0
        },
        {
            "type": "multi_choice",
            "prompt_markdown": "Quels répertoires de la norme **FHS (Filesystem Hierarchy Standard)** contiennent des fichiers de configuration système ou des journaux (logs) ? *(Plusieurs réponses)*",
            "points": 1.0,
            "options": ["/etc", "/var/log", "/bin", "/home"],
            "correct_answers": [0, 1]
        },
        {
            "type": "boolean",
            "prompt_markdown": "Sous Linux/POSIX, l'utilisateur super-administrateur `root` possède toujours l'identifiant numérique **UID 0**.",
            "points": 1.0,
            "options": [],
            "correct_answers": True
        },
        {
            "type": "fill_blank",
            "prompt_markdown": "Quelle commande POSIX permet de modifier le propriétaire (utilisateur et/ou groupe) d'un fichier ou répertoire sous Linux ? `_____`",
            "points": 1.0,
            "options": [],
            "correct_answers": ["chown"]
        },
        {
            "type": "matching",
            "prompt_markdown": "Associez chaque commande d'administration Linux à sa fonction exacte :",
            "points": 1.0,
            "options": [
                {"left": "ps aux / top", "right": "Inspecter les processus actifs en mémoire"},
                {"left": "df -h", "right": "Afficher l'espace disque disponible sur les systèmes de fichiers montés"},
                {"left": "systemctl status", "right": "Vérifier l'état d'un démon ou service géré par systemd"}
            ],
            "correct_answers": {
                "ps aux / top": "Inspecter les processus actifs en mémoire",
                "df -h": "Afficher l'espace disque disponible sur les systèmes de fichiers montés",
                "systemctl status": "Vérifier l'état d'un démon ou service géré par systemd"
            }
        }
    ]
    for q in base_5:
        seen.add(q["prompt_markdown"].strip())
        questions.append(q)

    curr_path = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data", "linux_training", "curriculum.json")
    if os.path.exists(curr_path):
        with open(curr_path, "r", encoding="utf-8") as f:
            curr = json.load(f)
        for ch in curr.get("chapters", []):
            for q in ch.get("mcq_questions", []):
                prompt = (q.get("prompt") or q.get("prompt_markdown", "")).strip()
                if prompt and prompt not in seen:
                    seen.add(prompt)
                    raw_opts = q.get("options", [])
                    norm_opts = []
                    if isinstance(raw_opts, list):
                        for o in raw_opts:
                            if isinstance(o, dict) and "text" in o:
                                norm_opts.append(o["text"])
                            else:
                                norm_opts.append(str(o))
                    else:
                        norm_opts = raw_opts
                    questions.append({
                        "type": q.get("type", "single_choice"),
                        "prompt_markdown": prompt,
                        "points": 1.0,
                        "options": norm_opts,
                        "correct_answers": q.get("correct", 0)
                    })
                if len(questions) >= 40:
                    break
            if len(questions) >= 40:
                break

    return questions[:40]


def reset_and_seed_3_exams(db=None, clear_practice=False):
    close_db = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_db = True
        clear_practice = True

    try:
        # 1. PURGE TOTALE DES EXAMENS & TENTATIVES D'EXAMEN
        db.query(StudentAnswer).delete()
        db.query(AuditLog).delete()
        db.query(StudentAttempt).delete()
        db.query(ExamSession).delete()
        db.query(Question).delete()
        db.execute(exam_groups.delete())
        db.query(Exam).delete()
        if clear_practice:
            db.query(PracticeAttempt).delete()
            db.query(TrainingAttempt).delete()
            db.query(ChapterProgress).delete()
        db.commit()

        # 2. INSERTION DES 3 MODULES DE TEST (+ ALGO pour compatibilité bulletins) & PURGE DES MODULES PARASITES
        valid_module_codes = {"PYTHON_INIT", "CRYPTO", "LINUX_ADMIN", "ALGO"}
        if clear_practice:
            db.execute(teacher_modules.delete())
            extra_mods = db.query(Module).filter(~Module.code.in_(valid_module_codes)).all()
            for em in extra_mods:
                db.delete(em)
            db.commit()
        else:
            # Toujours supprimer les modules temporaires CLOUD_* ou modules hors périmètre sans examen
            parasitic_mods = db.query(Module).filter(
                (Module.code.like("CLOUD_%")) |
                (Module.code.in_(["DEV_WEB", "DATABASE_SQL", "NETWORKS", "AI_ML", "DATA_STRUCT"]))
            ).all()
            for pm in parasitic_mods:
                db.delete(pm)
            db.commit()

        modules_data = [
            ("PYTHON_INIT", "Programmation Python & Algorithmique", "Fondamentaux du langage Python, structures de données et résolution algorithmique."),
            ("CRYPTO", "Cryptographie & Sécurité", "Chiffrement symétrique, asymétrique, hachage cryptographique, PKI et protocoles."),
            ("LINUX_ADMIN", "Administration Système Linux", "Arborescence POSIX/FHS, permissions, processus, gestion réseau et scripts Bash."),
            ("ALGO", "Algorithmique Fondamentale", "Complexité algorithmique, structures de données et récursivité."),
        ]
        mod_map = {}
        for code, title, desc in modules_data:
            mod = db.query(Module).filter(Module.code == code).first()
            if not mod:
                mod = Module(code=code, title=title, description=desc)
                db.add(mod)
                db.flush()
            else:
                mod.title = title
                mod.description = desc
            mod_map[code] = mod
        db.commit()

        # 3. INSERTION DE L'ADMIN ET DES ENSEIGNANTS PAR MODULE
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                id="ADM-001",
                username="admin",
                password_hash=hash_password("Admin123!"),
                plain_password="Admin123!",
                full_name="Administrateur Principal",
                email="admin@ecole.fr",
                role="admin",
                is_active=True,
                must_change_password=False
            )
            db.add(admin)
        else:
            admin.plain_password = admin.plain_password or "Admin123!"

        teachers_spec = [
            ("TCH-001", "prof_martin", "prof123", "Dr. Martin Laurent", "martin.laurent@ecole.fr", ["PYTHON_INIT", "CRYPTO", "LINUX_ADMIN", "ALGO"]),
            ("TCH-PYTHON", "prof_python", "ProfPython1!", "Dr. Martin Laurent (Resp. Python)", "martin.python@ecole.fr", ["PYTHON_INIT"]),
            ("TCH-CRYPTO", "prof_crypto", "ProfCrypto1!", "Dr. Sophie Bernard (Resp. Crypto)", "sophie.crypto@ecole.fr", ["CRYPTO"]),
            ("TCH-LINUX", "prof_linux", "ProfLinux1!", "Dr. Karim Mansouri (Resp. Linux)", "karim.linux@ecole.fr", ["LINUX_ADMIN"]),
        ]
        teacher_objs = {}
        for t_id, t_user, t_pwd, t_name, t_mail, t_mods in teachers_spec:
            t_obj = db.query(User).filter(User.username == t_user).first()
            if not t_obj:
                t_obj = User(
                    id=t_id,
                    username=t_user,
                    password_hash=hash_password(t_pwd),
                    plain_password=t_pwd,
                    full_name=t_name,
                    email=t_mail,
                    role="teacher",
                    is_active=True,
                    must_change_password=False
                )
                db.add(t_obj)
                db.flush()
            else:
                t_obj.plain_password = t_pwd
                t_obj.full_name = t_name
                t_obj.email = t_mail
            t_obj.assigned_modules = [mod_map[m_code] for m_code in t_mods if m_code in mod_map]
            teacher_objs[t_user] = t_obj
        db.commit()

        # 4. CRÉATION DES 4 SPÉCIALITÉS / CLASSES (GROUPES)
        groups_data = [
            ("DEV-IA", "Spécialité 1 : Développement & IA", "Promotion Développement Logiciel, Python & Intelligence Artificielle (4 étudiants)"),
            ("SYS-ADMIN", "Spécialité 2 : Systèmes & Réseaux Linux", "Promotion Administration Systèmes POSIX, Réseaux & Cloud (4 étudiants)"),
            ("CYBER-SEC", "Spécialité 3 : Cybersécurité & Cryptographie", "Promotion Sécurité de l'Information, Cryptographie & Audit (4 étudiants)"),
            ("GRP-1", "Spécialité 4 : Génie Logiciel & Systèmes (Groupe 1)", "Promotion Ingénierie Logicielle & Systèmes Embarqués (4 étudiants)"),
        ]
        valid_group_ids = {g[0] for g in groups_data}
        group_objs = []
        for gid, gname, gdesc in groups_data:
            grp = db.query(Group).filter(Group.id == gid).first()
            if not grp:
                grp = Group(id=gid, name=gname, description=gdesc)
                db.add(grp)
                db.flush()
            else:
                grp.name = gname
                grp.description = gdesc
            group_objs.append(grp)
        db.commit()

        # 5. CRÉATION DES 16 ÉTUDIANTS (4 SPÉCIALITÉS × 4 ÉTUDIANTS AVEC TOUTES LEURS INFORMATIONS)
        students_data = [
            # Spécialité 1 : DEV-IA (4 étudiants)
            ("ETU-ETU_DEV1", "etu_dev1", "StudentDev1!", "Alice Dev (IA-1)", "alice.dev@exam.local", "DEV-IA", "2025-2026"),
            ("ETU-ETU_DEV2", "etu_dev2", "StudentDev2!", "Bob Dev (IA-2)", "bob.dev@exam.local", "DEV-IA", "2025-2026"),
            ("ETU-ETU_DEV3", "etu_dev3", "StudentDev3!", "Clara Dev (IA-3)", "clara.dev@exam.local", "DEV-IA", "2025-2026"),
            ("ETU-ETU_DEV4", "etu_dev4", "StudentDev4!", "David Dev (IA-4)", "david.dev@exam.local", "DEV-IA", "2025-2026"),
            # Spécialité 2 : SYS-ADMIN (4 étudiants)
            ("ETU-ETU_SYS1", "etu_sys1", "StudentSys1!", "Emma Sys (Linux-1)", "emma.sys@exam.local", "SYS-ADMIN", "2025-2026"),
            ("ETU-ETU_SYS2", "etu_sys2", "StudentSys2!", "Fares Sys (Linux-2)", "fares.sys@exam.local", "SYS-ADMIN", "2025-2026"),
            ("ETU-ETU_SYS3", "etu_sys3", "StudentSys3!", "Gilles Sys (Linux-3)", "gilles.sys@exam.local", "SYS-ADMIN", "2025-2026"),
            ("ETU-ETU_SYS4", "etu_sys4", "StudentSys4!", "Hajar Sys (Linux-4)", "hajar.sys@exam.local", "SYS-ADMIN", "2025-2026"),
            # Spécialité 3 : CYBER-SEC (4 étudiants)
            ("ETU-ETU_SEC1", "etu_sec1", "StudentSec1!", "Ines Sec (Crypto-1)", "ines.sec@exam.local", "CYBER-SEC", "2025-2026"),
            ("ETU-ETU_SEC2", "etu_sec2", "StudentSec2!", "Jules Sec (Crypto-2)", "jules.sec@exam.local", "CYBER-SEC", "2025-2026"),
            ("ETU-ETU_SEC3", "etu_sec3", "StudentSec3!", "Karim Sec (Crypto-3)", "karim.sec@exam.local", "CYBER-SEC", "2025-2026"),
            ("ETU-ETU_SEC4", "etu_sec4", "StudentSec4!", "Lena Sec (Crypto-4)", "lena.sec@exam.local", "CYBER-SEC", "2025-2026"),
            # Spécialité 4 : GRP-1 (4 étudiants)
            ("ETU-001", "etudiant1", "etu123", "Alice Dupont (GL-1)", "etudiant1@exam.local", "GRP-1", "2025-2026"),
            ("ETU-ETU_LOG2", "etu_log2", "StudentLog2!", "Thomas Garnier (GL-2)", "thomas.log@exam.local", "GRP-1", "2025-2026"),
            ("ETU-ETU_LOG3", "etu_log3", "StudentLog3!", "Camille Chevalier (GL-3)", "camille.log@exam.local", "GRP-1", "2025-2026"),
            ("ETU-ETU_LOG4", "etu_log4", "StudentLog4!", "Maxime Lambert (GL-4)", "maxime.log@exam.local", "GRP-1", "2025-2026"),
        ]
        valid_student_usernames = {s[1] for s in students_data}
        for sid, uname, pwd, fname, email, gid, year in students_data:
            stu = db.query(User).filter(User.username == uname).first()
            if not stu:
                stu = User(
                    id=sid,
                    username=uname,
                    password_hash=hash_password(pwd),
                    plain_password=pwd,
                    full_name=fname,
                    email=email,
                    role="student",
                    group_id=gid,
                    enrollment_year=year,
                    is_active=True,
                    must_change_password=False
                )
                db.add(stu)
            else:
                stu.plain_password = pwd
                stu.full_name = fname
                stu.email = email
                stu.group_id = gid
                stu.enrollment_year = year

        if clear_practice:
            extra_students = db.query(User).filter(
                User.role == "student",
                ~User.username.in_(valid_student_usernames)
            ).all()
            for es in extra_students:
                db.delete(es)
            extra_groups = db.query(Group).filter(~Group.id.in_(valid_group_ids)).all()
            for eg in extra_groups:
                db.delete(eg)
        db.commit()

        # =========================================================================
        # 6. EXAMENS MODÈLES POUR LES 3 MODULES (PYTHON_INIT, CRYPTO, LINUX_ADMIN)
        # =========================================================================

        # --- MODULE 1 : PYTHON_INIT (Volet Théorique : 40 questions -> 20 aléatoires/étudiant) ---
        exam_theo_py = Exam(
            id="EXAM-THEO-PYTHON",
            module_code="PYTHON_INIT",
            title="Théorie Python",
            exam_type="theoretical",
            instructions="Épreuve officielle théorique de programmation Python (Banque de 40 questions : tirage aléatoire de 20 questions par étudiant, ordre des questions et des choix mélangés). [CONFIG_RANDOM_STUDENT_QUESTIONS=20]",
            duration_minutes=45,
            global_points=20.0,
            shuffle_questions=True,
            shuffle_options=True,
            created_by=teacher_objs["prof_python"].id
        )
        exam_theo_py.groups = list(group_objs)
        db.add(exam_theo_py)
        db.flush()

        q_theo_python = [
            Question(
                id="Q-TPY-1", exam_id=exam_theo_py.id, ordering=1, type="single_choice",
                prompt_markdown="Quelle est la sortie exacte de l'expression Python `[x**2 for x in range(4) if x % 2 == 0]` ?",
                points=1.0,
                options_json=json.dumps(["[0, 4]", "[0, 1, 4, 9]", "[4, 16]", "[2, 4]"]),
                correct_answers_json=json.dumps(0)
            ),
            Question(
                id="Q-TPY-2", exam_id=exam_theo_py.id, ordering=2, type="multi_choice",
                prompt_markdown="Parmi les types suivants en Python, lesquels sont **immuables** (immutable) ? *(Plusieurs réponses)*",
                points=1.0,
                options_json=json.dumps(["tuple", "list", "str", "dict", "frozenset"]),
                correct_answers_json=json.dumps([0, 2, 4])
            ),
            Question(
                id="Q-TPY-3", exam_id=exam_theo_py.id, ordering=3, type="boolean",
                prompt_markdown="En Python 3, l'opérateur `//` effectue toujours une division entière (floor division).",
                points=1.0,
                options_json=json.dumps([]),
                correct_answers_json=json.dumps(True)
            ),
            Question(
                id="Q-TPY-4", exam_id=exam_theo_py.id, ordering=4, type="fill_blank",
                prompt_markdown="Quel mot-clé Python permet de définir une fonction génératrice qui produit des valeurs à la demande ? `_____`",
                points=1.0,
                options_json=json.dumps([]),
                correct_answers_json=json.dumps(["yield"])
            ),
            Question(
                id="Q-TPY-5", exam_id=exam_theo_py.id, ordering=5, type="matching",
                prompt_markdown="Associez chaque méthode ou fonction Python à son rôle exact :",
                points=1.0,
                options_json=json.dumps([
                    {"left": "len(obj)", "right": "Retourne le nombre d'éléments d'une collection"},
                    {"left": "enumerate(it)", "right": "Fournit des tuples (indice, valeur) lors d'une itération"},
                    {"left": "zip(a, b)", "right": "Agrège en parallèle les éléments de plusieurs itérables"}
                ]),
                correct_answers_json=json.dumps({
                    "len(obj)": "Retourne le nombre d'éléments d'une collection",
                    "enumerate(it)": "Fournit des tuples (indice, valeur) lors d'une itération",
                    "zip(a, b)": "Agrège en parallèle les éléments de plusieurs itérables"
                })
            ),
        ]
        extra_35 = _load_extra_35_python_mcqs()
        for idx, eq in enumerate(extra_35, start=6):
            q_theo_python.append(Question(
                id=f"Q-TPY-{idx}",
                exam_id=exam_theo_py.id,
                ordering=idx,
                type=eq.get("type", "single_choice"),
                prompt_markdown=eq["prompt_markdown"],
                points=1.0,
                negative_penalty=eq.get("negative_penalty", 0.0),
                options_json=json.dumps(eq["options"], ensure_ascii=False),
                correct_answers_json=json.dumps(eq["correct_answers"], ensure_ascii=False)
            ))

        for q in q_theo_python:
            db.add(q)

        # Volet Pratique Python
        exam_prac_py = Exam(
            id="EXAM-PRAC-PYTHON",
            module_code="PYTHON_INIT",
            title="Pratique Python",
            exam_type="practical",
            instructions="Épreuve officielle pratique sur machine : 5 défis algorithmiques Python évalués sur jeux de tests publics et cachés.",
            duration_minutes=60,
            global_points=20.0,
            shuffle_questions=True,
            shuffle_options=True,
            created_by=teacher_objs["prof_python"].id
        )
        exam_prac_py.groups = list(group_objs)
        db.add(exam_prac_py)
        db.flush()

        challenges_path = os.path.join(
            os.path.dirname(__file__), "..", "backend", "app", "data", "python_training", "coding_challenges.json"
        )
        selected_challenges = []
        if os.path.exists(challenges_path):
            with open(challenges_path, "r", encoding="utf-8") as f:
                all_ch = json.load(f)
                selected_challenges = all_ch[:5]

        for idx, ch in enumerate(selected_challenges, start=1):
            pub_tests = ch.get("public_tests", [])
            hid_tests = ch.get("hidden_tests", [])
            db.add(Question(
                id=f"Q-PPY-{idx}",
                exam_id=exam_prac_py.id,
                ordering=idx,
                type="code_python",
                prompt_markdown=f"### {ch['title']}\n\n{ch['description']}",
                points=4.0,
                options_json=json.dumps({
                    "starter_code": ch.get("starter_code", "# Écrivez votre solution ici\n"),
                    "public_tests": pub_tests,
                    "challenge_id": ch.get("id", f"PY-CH-{idx:02d}"),
                    "difficulty": ch.get("difficulty", "Facile"),
                    "chapter": ch.get("chapter", "Algorithmique Python"),
                    "hint1": ch.get("hint1", "Analysez le format d'entrée standard avec input() et affichez le résultat avec print()."),
                    "hint2": ch.get("hint2", ch.get("solution", ""))
                }),
                correct_answers_json=json.dumps({
                    "public_tests": pub_tests,
                    "hidden_tests": hid_tests,
                    "solution": ch.get("solution", ""),
                    "explanation": ch.get("explanation", "")
                })
            ))

        # --- MODULE 2 : CRYPTO (Épreuve Modèle Cryptographie & Sécurité : 40 questions -> 20 aléatoires/étudiant) ---
        exam_theo_crypto = Exam(
            id="EXAM-THEO-CRYPTO",
            module_code="CRYPTO",
            title="Cryptographie & Sécurité",
            exam_type="theoretical",
            instructions="Épreuve officielle théorique de Cryptographie & Sécurité de l'Information (Banque de 40 questions : tirage aléatoire de 20 questions par étudiant, ordre des questions et des choix mélangés). [CONFIG_RANDOM_STUDENT_QUESTIONS=20]",
            duration_minutes=45,
            global_points=20.0,
            shuffle_questions=True,
            shuffle_options=True,
            created_by=teacher_objs["prof_crypto"].id
        )
        exam_theo_crypto.groups = list(group_objs)
        db.add(exam_theo_crypto)
        db.flush()

        crypto_40 = _load_40_crypto_questions()
        for idx, q_data in enumerate(crypto_40, start=1):
            db.add(Question(
                id=f"Q-TCRY-{idx}",
                exam_id=exam_theo_crypto.id,
                ordering=idx,
                type=q_data.get("type", "single_choice"),
                prompt_markdown=q_data["prompt_markdown"],
                points=1.0,
                negative_penalty=q_data.get("negative_penalty", 0.0),
                options_json=json.dumps(q_data["options"], ensure_ascii=False),
                correct_answers_json=json.dumps(q_data["correct_answers"], ensure_ascii=False)
            ))

        # --- MODULE 3 : LINUX_ADMIN (Épreuve Modèle Administration Système Linux : 40 questions -> 20 aléatoires/étudiant) ---
        exam_theo_linux = Exam(
            id="EXAM-THEO-LINUX",
            module_code="LINUX_ADMIN",
            title="Administration Système Linux",
            exam_type="theoretical",
            instructions="Épreuve officielle théorique d'Administration Système Linux (Banque de 40 questions : tirage aléatoire de 20 questions par étudiant, ordre des questions et des choix mélangés). [CONFIG_RANDOM_STUDENT_QUESTIONS=20]",
            duration_minutes=45,
            global_points=20.0,
            shuffle_questions=True,
            shuffle_options=True,
            created_by=teacher_objs["prof_linux"].id
        )
        exam_theo_linux.groups = list(group_objs)
        db.add(exam_theo_linux)
        db.flush()

        linux_40 = _load_40_linux_questions()
        for idx, q_data in enumerate(linux_40, start=1):
            db.add(Question(
                id=f"Q-TLNX-{idx}",
                exam_id=exam_theo_linux.id,
                ordering=idx,
                type=q_data.get("type", "single_choice"),
                prompt_markdown=q_data["prompt_markdown"],
                points=1.0,
                negative_penalty=q_data.get("negative_penalty", 0.0),
                options_json=json.dumps(q_data["options"], ensure_ascii=False),
                correct_answers_json=json.dumps(q_data["correct_answers"], ensure_ascii=False)
            ))

        db.commit()
        print("Base de donnees initialisee avec succes :")
        print("  - 1 Administrateur (admin)")
        print("  - 4 Enseignants assignes aux 3 modules (prof_python, prof_crypto, prof_linux, prof_martin)")
        print("  - 4 Specialites x 4 Etudiants = 16 Etudiants complets (DEV-IA, SYS-ADMIN, CYBER-SEC, GRP-1)")
        print("  - 4 Examens officiels modeles crees :")
        print("      * Theorie Python (40Q banque -> 20 selectionnees)")
        print("      * Pratique Python (5 defis)")
        print("      * Cryptographie & Securite (40Q banque -> 20 selectionnees)")
        print("      * Administration Systeme Linux (40Q banque -> 20 selectionnees)")
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    reset_and_seed_3_exams()
