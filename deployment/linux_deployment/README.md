# 🐧 Guide de Déploiement Linux — Serveur Autonome d'Examen

Ce dossier est **100% autonome (self-contained)** pour déployer la plateforme d'examen sur tout serveur **Linux (Ubuntu, Debian, CentOS, RHEL, Alpine)** avec ou sans connexion Internet.

---

## ⚡ 1. Démarrage Rapide en 1 Commande

### Avec Docker & Docker Compose (Recommandé) :
```bash
# 1. Rendre les scripts exécutables
chmod +x *.sh

# 2. Démarrer la plateforme (Serveur FastAPI + PostgreSQL 16)
./start_server.sh
```
> Le serveur écoute immédiatement sur le port **8000** :  
> 👉 **http://localhost:8000** ou **http://<IP_DU_SERVEUR>:8000**

### Pour arrêter le serveur proprement :
```bash
./stop_server.sh
```

---

## 📦 2. Déploiement Hors-Ligne (Clé USB / Sans Internet)

Si votre serveur de salle d'examen n'a pas accès à Internet :
1. Copiez ce dossier complet `linux_deployment/` sur votre serveur.
2. Chargez l'image Docker binaire pré-empaquetée dans le moteur Docker :
   ```bash
   docker load -i images_docker/examination-quiz-server.tar
   ```
3. Lancez les conteneurs :
   ```bash
   docker compose up -d
   ```

---

## 🔑 3. Répertoire Complet des Identifiants (Logins)

Les identifiants complets sont stockés dans [`logins.txt`](./logins.txt) et [`identifiants/logins.txt`](./identifiants/logins.txt) :

### A. Administrateur Global
| Rôle | Identifiant | Mot de Passe | Description |
| :--- | :--- | :--- | :--- |
| **Super-Admin** | `admin` | `admin123` | Gestion globale, supervision des salles, réinitialisation de mots de passe, audit. |

### B. Enseignants par Module d'Examen
| ID Enseignant | Identifiant | Mot de Passe | Nom Enseignant | Module(s) Affecté(s) |
| :--- | :--- | :--- | :--- | :--- |
| `TCH-PYTHON` | `prof_python` | `ProfPython1!` | Dr. Martin Laurent | **PYTHON_INIT** |
| `TCH-CRYPTO` | `prof_crypto` | `ProfCrypto1!` | Dr. Sophie Bernard | **CRYPTO** |
| `TCH-LINUX` | `prof_linux` | `ProfLinux1!` | Dr. Karim Mansouri | **LINUX_ADMIN** |
| `TCH-001` | `prof_martin` | `prof123` | Dr. Martin Laurent | Tous les modules (Responsable Pédagogique) |

### C. Étudiants Répartis par Spécialité (16 Étudiants)
| Spécialité | Identifiant | Mot de Passe | Nom & Prénom | Matricule |
| :--- | :--- | :--- | :--- | :--- |
| **DEV-IA** | `etu_dev1` | `StudentDev1!` | Alice Dev (IA-1) | `ETU-ETU_DEV1` |
| **DEV-IA** | `etu_dev2` | `StudentDev2!` | Bob Dev (IA-2) | `ETU-ETU_DEV2` |
| **DEV-IA** | `etu_dev3` | `StudentDev3!` | Clara Dev (IA-3) | `ETU-ETU_DEV3` |
| **DEV-IA** | `etu_dev4` | `StudentDev4!` | David Dev (IA-4) | `ETU-ETU_DEV4` |
| **SYS-ADMIN** | `etu_sys1` | `StudentSys1!` | Emma Sys (Linux-1) | `ETU-ETU_SYS1` |
| **SYS-ADMIN** | `etu_sys2` | `StudentSys2!` | Fares Sys (Linux-2) | `ETU-ETU_SYS2` |
| **SYS-ADMIN** | `etu_sys3` | `StudentSys3!` | Gilles Sys (Linux-3) | `ETU-ETU_SYS3` |
| **SYS-ADMIN** | `etu_sys4` | `StudentSys4!` | Hajar Sys (Linux-4) | `ETU-ETU_SYS4` |
| **CYBER-SEC** | `etu_sec1` | `StudentSec1!` | Ines Sec (Crypto-1) | `ETU-ETU_SEC1` |
| **CYBER-SEC** | `etu_sec2` | `StudentSec2!` | Jules Sec (Crypto-2) | `ETU-ETU_SEC2` |
| **CYBER-SEC** | `etu_sec3` | `StudentSec3!` | Karim Sec (Crypto-3) | `ETU-ETU_SEC3` |
| **CYBER-SEC** | `etu_sec4` | `StudentSec4!` | Lena Sec (Crypto-4) | `ETU-ETU_SEC4` |
| **GRP-1 (Logiciel)** | `etudiant1` | `etu123` | Alice Dupont (GL-1) | `ETU-001` |
| **GRP-1 (Logiciel)** | `etu_log2` | `StudentLog2!` | Thomas Garnier (GL-2) | `ETU-ETU_LOG2` |
| **GRP-1 (Logiciel)** | `etu_log3` | `StudentLog3!` | Camille Chevalier (GL-3) | `ETU-ETU_LOG3` |
| **GRP-1 (Logiciel)** | `etu_log4` | `StudentLog4!` | Maxime Lambert (GL-4) | `ETU-ETU_LOG4` |

---

## 📂 4. Fichiers d'Injection et Données Utilisateurs

Tous les fichiers sources sont prêts dans leurs sous-dossiers respectifs :

### A. Listes Utilisateurs au format CSV :
- `csv_utilisateurs/enseignants_modules.csv` : Liste des professeurs avec leurs modules respectifs.
- `csv_utilisateurs/etudiants_4_specialites.csv` : Liste complète des étudiants par spécialité.
- `csv_utilisateurs/plan_salle_template.csv` : Modèle de disposition physique de la salle (étiquetage des machines).

### B. Modèles d'Examens au format JSON :
- `examens_json/examen_modele_python_avance.json` : Épreuve complète Python Avancé avec questions théoriques, épreuves pratiques et tests unitaires cachés.
- `examens_json/examen_modele_linux.json` : Épreuve complète Administration Linux & Bash.
- `examens_json/examen_modele_crypto.json` : Épreuve complète Cryptographie & Sécurité.
- `backups/all_exams_backup.json` : Sauvegarde globale de l'ensemble des banques d'examens.

---

## 🛠️ 5. Comment Réinjecter ou Réinitialiser les Examens et Utilisateurs

### Méthode 1 : Réinitialisation automatique via le script inclus
```bash
./init_test_db.sh
```
Ce script vide la base et injecte instantanément les 3 examens officiels, les 4 comptes professeurs et les 16 comptes étudiants.

### Méthode 2 : Importation manuelle depuis l'interface Web Enseignant
1. Connectez-vous avec un compte professeur (ex: `prof_python` / `ProfPython1!`).
2. Rendez-vous dans **"Gestion des Épreuves"** $\to$ **"Importer un Examen JSON"**.
3. Sélectionnez l'un des fichiers dans `examens_json/`.

---

## ⚙️ 6. Service Systemd (Démarrage Automatique au Boot Linux)
Pour que la plateforme se lance toute seule au démarrage du serveur physique :
```bash
sudo cp examquiz.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable examquiz.service
sudo systemctl start examquiz.service
```

