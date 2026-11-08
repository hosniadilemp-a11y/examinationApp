# 🪟 Guide de Déploiement Windows Server — Serveur Autonome d'Examen

Ce dossier est **100% autonome (self-contained)** pour déployer la plateforme d'examen sur un serveur **Windows (Windows Server 2019/2022 ou Windows 10/11 Pro)** avec ou sans connexion Internet.

---

## ⚡ 1. Démarrage Rapide en 1 Clic

### Démarrage des conteneurs applicatifs :
Double-cliquez directement sur :
👉 [**`start_server.bat`**](./start_server.bat)
*(Ou exécutez dans un terminal PowerShell Administrateur : `.\start_server.bat`)*

> Le serveur FastAPI et la base PostgreSQL 16 démarrent immédiatement.  
> 👉 Accès local : **http://localhost:8000** ou **http://exam.local:8000**

### 🚀 Déblocage Réseau Câblé (Switch 100% Ethernet sans Wi-Fi) :
Si les ordinateurs étudiants ne parviennent pas à joindre le serveur par câble réseau, faites un clic droit sur :
👉 [**`debloquer_acces_lan.bat`**](./debloquer_acces_lan.bat) > **"Exécuter en tant qu'administrateur"**
*(Ce script ouvre le pare-feu sur tous les profils de réseau, bascule l'interface en mode Privé et crée le pont PortProxy WSL2).*

### Pour arrêter le serveur :
Double-cliquez sur :
👉 [**`stop_server.bat`**](./stop_server.bat)

---

## 📦 2. Déploiement Hors-Ligne (Clé USB / Sans Internet)

1. Branchez votre clé USB contenant ce dossier `windows_deployment/`.
2. Lancez le script de chargement d'image :
   👉 [**`load_offline_image.bat`**](./load_offline_image.bat)  
   *(Ce script charge automatiquement `images_docker/examination-quiz-server.tar` dans le moteur Docker local).*
3. Double-cliquez sur `start_server.bat`.

---

## 🔗 3. Configuration de l'Accès Convivial Étudiant (`exam.local`)

Pour que tous les étudiants accèdent au serveur en tapant `http://exam.local:8000` au lieu de taper l'adresse IP numérique du serveur :
1. Copiez le script [**`installer_nom_local.bat`**](./installer_nom_local.bat) sur votre clé USB.
2. Double-cliquez sur ce script sur chaque poste étudiant de la salle (en Administrateur).
3. Le domaine `exam.local` est enregistré instantanément en 1 seconde.

---

## 🔑 4. Répertoire Complet des Identifiants (Logins)

Les identifiants complets sont détaillés dans [`logins.txt`](./logins.txt) et [`identifiants/logins.txt`](./identifiants/logins.txt) :

### A. Administrateur Global
| Rôle | Identifiant | Mot de Passe | Description |
| :--- | :--- | :--- | :--- |
| **Super-Admin** | `admin` | `admin123` | Gestion globale, surveillance de salle, gestion des comptes et audit. |

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

## 📂 5. Fichiers d'Injection et Données Utilisateurs

- **`csv_utilisateurs/enseignants_modules.csv`** : Affectation des enseignants à leurs modules respectifs.
- **`csv_utilisateurs/etudiants_4_specialites.csv`** : Importation groupée des étudiants.
- **`csv_utilisateurs/plan_salle_template.csv`** : Modèle de disposition physique des machines.
- **`examens_json/examen_modele_python_avance.json`** : Épreuve officielle Python Avancé avec questions théoriques et cas pratiques.
- **`examens_json/examen_modele_linux.json`** : Épreuve officielle Administration Linux.
- **`examens_json/examen_modele_crypto.json`** : Épreuve officielle Cryptographie & Sécurité.
- **`backups/all_exams_backup.json`** : Sauvegarde JSON complète de toutes les banques d'épreuves.

---

## 🛠️ 6. Comment Réinjecter ou Réinitialiser les Examens et Utilisateurs

### Méthode 1 : Réinitialisation automatique via script
Double-cliquez sur :
👉 [**`init_test_db.bat`**](./init_test_db.bat)  
*(Réinitialise la base PostgreSQL ou SQLite et injecte instantanément les 3 examens officiels et les 20 comptes utilisateurs).*

### Méthode 2 : Importation depuis l'interface Web Enseignant
1. Connectez-vous avec `prof_python` ou `admin`.
2. Allez dans **"Gestion des Épreuves"** $\to$ **"Importer un Examen JSON"**.
3. Sélectionnez le fichier souhaité dans le dossier `examens_json/`.

