# 📦 Archive des Données & Banques d'Examens (`archive_data/`)

Ce dossier conserve l'intégralité des données de référence, modèles d'examens, banques de questions et sauvegardes de base de données avant la purge de pré-déploiement.

## 📂 Structure du Dossier

1. **`exams_backup/`**
   - `all_exams_backup.json` : Export JSON intégral des examens et questions existants avant réinitialisation pour le déploiement.
   - `exam_app_pre_deployment_snapshot.db` : Image SQLite complète de la base de données avant purge.

2. **`templates/`**
   - `template_exam_python.json` : Modèle d'examen officiel pour le module **Programmation Python (`PYTHON_INIT`)**.
   - `template_exam_crypto.json` : Modèle d'examen officiel pour le module **Cryptographie & Sécurité (`CRYPTO`)**.
   - `template_exam_linux.json` : Modèle d'examen officiel pour le module **Administration Système Linux (`LINUX_ADMIN`)**.

3. **`question_banks/`**
   - `seed_python_30.json` : Banque officielle de 30 questions théoriques Python.
   - `seed_crypto_30.json` : Banque officielle de 30 questions théoriques Cryptographie.
   - `seed_linux_30.json` : Banque officielle de 30 questions théoriques Administration Linux.
   - `seed_algo_30.json` : Banque officielle de 30 questions Algorithmique.
   - `python_training/curriculum.json` : 10 chapitres Python complets (414 QCM + 183 exercices pratiques avec indices, solutions complètes et explications détaillées).
   - `python_training/coding_challenges.json` : 47 défis algorithmiques Python gradués (2 tests publics + 10 tests cachés par défi, solutions et explications pédagogiques).
   - `linux_training/curriculum.json` & `challenges.json` : Cursus complet POSIX/Linux et défis de terminal VFS.

## 🔄 Restauration ou Importation Manuelle

- Pour réinitialiser la base de données avec la configuration officielle de déploiement (Admin, 3 modules avec leurs enseignants dédiés, 4 classes de 4 étudiants, et les examens modèles), exécutez :
  ```bash
  python scripts/reset_and_seed_exact_3_exams.py
  ```
- Pour importer un modèle JSON depuis l'interface Enseignant ou Administrateur, utilisez le bouton **Importer JSON** et sélectionnez un fichier dans `archive_data/templates/`.

