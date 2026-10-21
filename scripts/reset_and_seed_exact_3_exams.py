import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timezone
from backend.app.database import get_db
from backend.app.models import Exam, Question, Group, Module, User, ExamSession, StudentAttempt, StudentAnswer, AuditLog

def reset_and_seed_3_exams(db=None):
    close_db = False
    if db is None:
        db = next(get_db())
        close_db = True
    print("[RESET] Nettoyage complet des anciens examens d'exemple...")

    # 1. Supprimer toutes les tentatives, réponses, sessions et questions associées aux anciens examens
    db.query(StudentAnswer).delete()
    db.query(StudentAttempt).delete()
    db.query(AuditLog).delete()
    db.query(ExamSession).delete()
    db.query(Question).delete()

    # Détacher les associations de groupes existantes
    all_exams = db.query(Exam).all()
    for ex in all_exams:
      ex.groups.clear()
    db.flush()

    # Supprimer tous les examens
    db.query(Exam).delete()
    db.commit()
    print("[RESET] Tous les anciens examens ont été purgés de la base.")

    # 2. Vérifier et assurer l'existence des groupes
    group_ids = ["DEV-IA", "SYS-ADMIN", "CYBER-SEC", "GRP-1", "GRP-2", "GRP-SEC-1"]
    groups = []
    for gid in group_ids:
      grp = db.query(Group).filter(Group.id == gid).first()
      if not grp:
        grp = Group(id=gid, name=f"Groupe {gid}")
        db.add(grp)
        db.flush()
      groups.append(grp)
    db.commit()

    # 3. Vérifier et assurer l'existence des modules
    mod_python = db.query(Module).filter(Module.code == "PYTHON_INIT").first()
    if not mod_python:
      mod_python = Module(code="PYTHON_INIT", title="Programmation Python Fondamentale")
      db.add(mod_python)

    mod_crypto = db.query(Module).filter(Module.code == "CRYPTO").first()
    if not mod_crypto:
      mod_crypto = Module(code="CRYPTO", title="Cryptographie & Sécurité Réseau")
      db.add(mod_crypto)
    db.commit()

    # Assigner prof_martin à ces modules
    prof = db.query(User).filter(User.username == "prof_martin").first()
    if prof:
      if mod_python not in prof.assigned_modules:
        prof.assigned_modules.append(mod_python)
      if mod_crypto not in prof.assigned_modules:
        prof.assigned_modules.append(mod_crypto)
      db.commit()

    # -------------------------------------------------------------------------
    # EXAMEN 1 : ÉPREUVE THÉORIQUE PYTHON (QCM & Connaissances)
    # -------------------------------------------------------------------------
    exam1 = Exam(
        id="EXAM-THEO-PYTHON",
        title="Épreuve Théorique : Python Fondamentaux & Algorithmique",
        module_code="PYTHON_INIT",
        exam_type="theoretical",
        duration_minutes=45,
        global_points=20.0,
        instructions="Épreuve officielle théorique à livre fermé. Calculatrices interdites. QCM, Vrai/Faux, Textes à trous et Appariements."
    )
    for g in groups:
      exam1.groups.append(g)
    db.add(exam1)
    db.flush()

    q1_1 = Question(
        id="Q-PY-THEO-1",
        exam_id=exam1.id,
        ordering=1,
        type="single_choice",
        points=4.0,
        prompt_markdown="En Python 3, parmi les types de données suivants, lequel est **immuable** (*immutable*) ?",
        options_json=json.dumps([
            {"id": "A", "text": "list (liste dynamique)"},
            {"id": "B", "text": "tuple (n-uplet)"},
            {"id": "C", "text": "set (ensemble)"},
            {"id": "D", "text": "dict (dictionnaire)"}
        ]),
        correct_answers_json=json.dumps(["B"])
    )

    q1_2 = Question(
        id="Q-PY-THEO-2",
        exam_id=exam1.id,
        ordering=2,
        type="multi_choice",
        points=4.0,
        prompt_markdown="Quelles sont les affirmations **vraies** concernant les compréhensions de listes en Python ?",
        options_json=json.dumps([
            {"id": "A", "text": "Elles permettent d'écrire un code plus concis et généralement plus rapide qu'une boucle for classique."},
            {"id": "B", "text": "Une compréhension de liste peut comporter une clause conditionnelle de filtrage `if`."},
            {"id": "C", "text": "Elles retournent toujours un objet de type générateur paresseux (generator)."},
            {"id": "D", "text": "L'expression `[x**2 for x in range(5) if x % 2 == 0]` produit `[0, 4, 16]`."}
        ]),
        correct_answers_json=json.dumps(["A", "B", "D"])
    )

    q1_3 = Question(
        id="Q-PY-THEO-3",
        exam_id=exam1.id,
        ordering=3,
        type="boolean",
        points=4.0,
        prompt_markdown="La recherche d'une clé dans un dictionnaire Python standard s'effectue en temps moyen de complexité $\\mathcal{O}(1)$ grâce à une table de hachage.",
        options_json=json.dumps([]),
        correct_answers_json=json.dumps(["true"])
    )

    q1_4 = Question(
        id="Q-PY-THEO-4",
        exam_id=exam1.id,
        ordering=4,
        type="fill_blank",
        points=4.0,
        prompt_markdown="Quel mot-clé Python est utilisé à l'intérieur d'une fonction pour retourner un générateur et produire des valeurs de manière paresseuse au lieu d'interrompre la fonction avec `return` ?",
        options_json=json.dumps([]),
        correct_answers_json=json.dumps(["yield"])
    )

    q1_5 = Question(
        id="Q-PY-THEO-5",
        exam_id=exam1.id,
        ordering=5,
        type="matching",
        points=4.0,
        prompt_markdown="Associez chaque module de la bibliothèque standard Python à son utilité principale :",
        options_json=json.dumps({
            "left": ["math", "json", "sys", "collections"],
            "right": [
                "Fonctions mathématiques et constantes (sqrt, pi, log)",
                "Sérialisation et désérialisation de données structurées",
                "Paramètres et interactions avec l'interpréteur Python",
                "Structures de données avancées (Counter, deque, defaultdict)"
            ]
        }),
        correct_answers_json=json.dumps({
            "math": "Fonctions mathématiques et constantes (sqrt, pi, log)",
            "json": "Sérialisation et désérialisation de données structurées",
            "sys": "Paramètres et interactions avec l'interpréteur Python",
            "collections": "Structures de données avancées (Counter, deque, defaultdict)"
        })
    )

    db.add_all([q1_1, q1_2, q1_3, q1_4, q1_5])
    db.commit()
    print("[SEED] Examen 1 créé : EXAM-THEO-PYTHON (5 questions théoriques, 20 pts)")

    # -------------------------------------------------------------------------
    # EXAMEN 2 : ÉPREUVE PRATIQUE PYTHON (Défis Machine AlgoCompiler)
    # -------------------------------------------------------------------------
    exam2 = Exam(
        id="EXAM-PRAC-PYTHON",
        title="Épreuve Pratique : Algorithmes & Défis Python",
        module_code="PYTHON_INIT",
        exam_type="practical",
        duration_minutes=60,
        global_points=20.0,
        instructions="Épreuve pratique sur machine. Écrivez des scripts Python conformes aux spécifications. Chaque défi est évalué sur des cas de tests publics et des cas secrets."
    )
    for g in groups:
      exam2.groups.append(g)
    db.add(exam2)
    db.flush()

    # Défi 1 : Somme des Nombres Pairs (6 pts)
    # 2 tests publics, 10 tests cachés
    pub_tests_1 = [
        {"input": "1 2 3 4 5 6", "output": "12", "is_public": True},
        {"input": "10 20 30", "output": "60", "is_public": True}
    ]
    hid_tests_1 = [
        {"input": "1 3 5 7 9", "output": "0", "is_public": False},
        {"input": "2 4 6 8 10", "output": "30", "is_public": False},
        {"input": "0 0 0", "output": "0", "is_public": False},
        {"input": "-2 -4 -6", "output": "-12", "is_public": False},
        {"input": "-1 -2 -3 4", "output": "2", "is_public": False},
        {"input": "100 201 300 401 500", "output": "900", "is_public": False},
        {"input": "42", "output": "42", "is_public": False},
        {"input": "99", "output": "0", "is_public": False},
        {"input": "12 14 16 18 20 22", "output": "102", "is_public": False},
        {"input": "5 10 15 20 25 30 35 40", "output": "100", "is_public": False}
    ]

    q2_1 = Question(
        id="Q-PY-PRAC-1",
        exam_id=exam2.id,
        ordering=1,
        type="coding",
        points=6.0,
        prompt_markdown=(
            "### Défi 1 : Somme des Nombres Pairs\n\n"
            "Écrivez un programme Python qui lit sur l'entrée standard une ligne d'entiers séparés par des espaces, "
            "calcule la somme uniquement des entiers **pairs**, et affiche le résultat sur la sortie standard.\n\n"
            "#### Entrée :\nUne suite d'entiers séparés par un espace.\n\n"
            "#### Sortie :\nUn entier unique représentant la somme des nombres pairs."
        ),
        options_json=json.dumps({
            "starter_code": "values = list(map(int, input().split()))\n\n# Calculez la somme des nombres pairs\n",
            "public_tests": pub_tests_1,
            "hidden_tests": hid_tests_1
        }),
        correct_answers_json=json.dumps(pub_tests_1 + hid_tests_1)
    )

    # Défi 2 : Inversion des Mots d'une Phrase (7 pts)
    pub_tests_2 = [
        {"input": "Bonjour tout le monde", "output": "monde le tout Bonjour", "is_public": True},
        {"input": "Python est formidable", "output": "formidable est Python", "is_public": True}
    ]
    hid_tests_2 = [
        {"input": "un", "output": "un", "is_public": False},
        {"input": "A B C D E", "output": "E D C B A", "is_public": False},
        {"input": "exam quiz plateforme", "output": "plateforme quiz exam", "is_public": False},
        {"input": "hello world", "output": "world hello", "is_public": False},
        {"input": "data science artificial intelligence", "output": "intelligence artificial science data", "is_public": False},
        {"input": "1 2 3 4 5", "output": "5 4 3 2 1", "is_public": False},
        {"input": "mot_unique", "output": "mot_unique", "is_public": False},
        {"input": "espace entre chaque terme", "output": "terme chaque entre espace", "is_public": False},
        {"input": "test securite sandbox", "output": "sandbox securite test", "is_public": False},
        {"input": "final verification complete", "output": "complete verification final", "is_public": False}
    ]

    q2_2 = Question(
        id="Q-PY-PRAC-2",
        exam_id=exam2.id,
        ordering=2,
        type="coding",
        points=7.0,
        prompt_markdown=(
            "### Défi 2 : Inversion des Mots d'une Phrase\n\n"
            "Écrivez un script Python qui lit une chaîne de caractères sur l'entrée standard et affiche les mots dans l'ordre inverse, "
            "séparés par un espace.\n\n"
            "#### Entrée :\nUne phrase composée de mots séparés par des espaces.\n\n"
            "#### Sortie :\nLa phrase dont l'ordre des mots est inversé."
        ),
        options_json=json.dumps({
            "starter_code": "sentence = input().strip()\n\n# Votre solution ici\n",
            "public_tests": pub_tests_2,
            "hidden_tests": hid_tests_2
        }),
        correct_answers_json=json.dumps(pub_tests_2 + hid_tests_2)
    )

    # Défi 3 : Validation des Parenthèses et Piles (7 pts)
    pub_tests_3 = [
        {"input": "()[]{}", "output": "VALID", "is_public": True},
        {"input": "([)]", "output": "INVALID", "is_public": True}
    ]
    hid_tests_3 = [
        {"input": "", "output": "VALID", "is_public": False},
        {"input": "((()))", "output": "VALID", "is_public": False},
        {"input": "{[()]}", "output": "VALID", "is_public": False},
        {"input": "((", "output": "INVALID", "is_public": False},
        {"input": "}}", "output": "INVALID", "is_public": False},
        {"input": "{[(])}", "output": "INVALID", "is_public": False},
        {"input": "()", "output": "VALID", "is_public": False},
        {"input": "([]){}", "output": "VALID", "is_public": False},
        {"input": "({[()]})", "output": "VALID", "is_public": False},
        {"input": "({[()]}", "output": "INVALID", "is_public": False}
    ]

    q2_3 = Question(
        id="Q-PY-PRAC-3",
        exam_id=exam2.id,
        ordering=3,
        type="coding",
        points=7.0,
        prompt_markdown=(
            "### Défi 3 : Validation des Délimiteurs (Parenthèses, Crochets, Accolades)\n\n"
            "Écrivez un algorithme utilisant une structure de **pile** (*stack*) pour vérifier si une séquence de délimiteurs `()[]{}` est bien formée.\n\n"
            "#### Règle de validation :\n"
            "- Chaque ouvrant doit être fermé par le même type de délimiteur.\n"
            "- Les délimiteurs doivent être fermés dans l'ordre exact.\n\n"
            "#### Sortie :\n`VALID` si la séquence est correcte, `INVALID` sinon."
        ),
        options_json=json.dumps({
            "starter_code": "s = input().strip()\n\n# Votre solution ici avec une pile\n",
            "public_tests": pub_tests_3,
            "hidden_tests": hid_tests_3
        }),
        correct_answers_json=json.dumps(pub_tests_3 + hid_tests_3)
    )

    db.add_all([q2_1, q2_2, q2_3])
    db.commit()
    print("[SEED] Examen 2 créé : EXAM-PRAC-PYTHON (3 défis pratiques avec 2 public + 10 hidden tests chacun, 20 pts)")

    # -------------------------------------------------------------------------
    # EXAMEN 3 : ÉPREUVE DE CRYPTOGRAPHIE (Test Théorique)
    # -------------------------------------------------------------------------
    exam3 = Exam(
        id="EXAM-THEO-CRYPTO",
        title="Épreuve Officielle : Cryptographie & Sécurité",
        module_code="CRYPTO",
        exam_type="theoretical",
        duration_minutes=45,
        global_points=20.0,
        instructions="Épreuve officielle de Cryptographie. Plein écran strict et surveillance active."
    )
    for g in groups:
      exam3.groups.append(g)
    db.add(exam3)
    db.flush()

    q3_1 = Question(
        id="Q-CRY-THEO-1",
        exam_id=exam3.id,
        ordering=1,
        type="single_choice",
        points=4.0,
        prompt_markdown="Parmi les algorithmes de chiffrement suivants, lequel est un algorithme **asymétrique** à clé publique ?",
        options_json=json.dumps([
            {"id": "A", "text": "AES (Advanced Encryption Standard)"},
            {"id": "B", "text": "ChaCha20"},
            {"id": "C", "text": "RSA (Rivest-Shamir-Adleman)"},
            {"id": "D", "text": "3DES (Triple DES)"}
        ]),
        correct_answers_json=json.dumps(["C"])
    )

    q3_2 = Question(
        id="Q-CRY-THEO-2",
        exam_id=exam3.id,
        ordering=2,
        type="multi_choice",
        points=4.0,
        prompt_markdown="Quelles sont les propriétés indispensables d'une **fonction de hachage cryptographique sécurisée** (ex: SHA-256) ?",
        options_json=json.dumps([
            {"id": "A", "text": "Résistance à la pré-image (irréversibilité)."},
            {"id": "B", "text": "Résistance aux collisions (deux entrées distinctes ne doivent pas donner la même empreinte)."},
            {"id": "C", "text": "La fonction doit être réversible avec une clé privée."},
            {"id": "D", "text": "Effet d'avalanche (une modification minime de l'entrée change radicalement l'empreinte)."}
        ]),
        correct_answers_json=json.dumps(["A", "B", "D"])
    )

    q3_3 = Question(
        id="Q-CRY-THEO-3",
        exam_id=exam3.id,
        ordering=3,
        type="boolean",
        points=4.0,
        prompt_markdown="La signature numérique d'un message s'effectue en chiffrant l'empreinte du message avec la **clé privée** de l'émetteur, garantissant ainsi l'authenticité et la non-répudiation.",
        options_json=json.dumps([]),
        correct_answers_json=json.dumps(["true"])
    )

    q3_4 = Question(
        id="Q-CRY-THEO-4",
        exam_id=exam3.id,
        ordering=4,
        type="fill_blank",
        points=4.0,
        prompt_markdown="Quel protocole d'échange de clés fondé sur le problème du logarithme discret permet à deux interlocuteurs de convenir d'une clé secrète commune sur un canal public sans jamais transmettre la clé ?",
        options_json=json.dumps([]),
        correct_answers_json=json.dumps(["Diffie-Hellman", "diffie hellman", "diffie-hellman"])
    )

    q3_5 = Question(
        id="Q-CRY-THEO-5",
        exam_id=exam3.id,
        ordering=5,
        type="matching",
        points=4.0,
        prompt_markdown="Associez chaque protocole ou standard de sécurité à son cas d'usage prédominant :",
        options_json=json.dumps({
            "left": ["TLS / HTTPS", "SSH", "PGP / GPG", "IPsec"],
            "right": [
                "Sécurisation des communications web de bout en bout",
                "Accès terminal et administration distante chiffrée",
                "Chiffrement et signature des courriels et fichiers",
                "Sécurisation des tunnels VPN au niveau réseau (IP)"
            ]
        }),
        correct_answers_json=json.dumps({
            "TLS / HTTPS": "Sécurisation des communications web de bout en bout",
            "SSH": "Accès terminal et administration distante chiffrée",
            "PGP / GPG": "Chiffrement et signature des courriels et fichiers",
            "IPsec": "Sécurisation des tunnels VPN au niveau réseau (IP)"
        })
    )

    db.add_all([q3_1, q3_2, q3_3, q3_4, q3_5])
    db.commit()
    print("[SEED] Examen 3 créé : EXAM-THEO-CRYPTO (5 questions de sécurité, 20 pts)")
    print("\n[SUCCESS] Exactement 3 examens propres configurés dans la base !")
    if close_db:
        db.close()

if __name__ == "__main__":
    reset_and_seed_3_exams()
