# 🎓 Guide de l'Application Desktop — Exam Control Master

Ce dossier est **100% autonome (self-contained)** et prêt pour les **enseignants, surveillants et responsables de salle d'examen**.  
Il contient l'exécutable Windows officiel compilé ([**`ExamControlMaster.exe`**](./ExamControlMaster.exe)) qui permet de piloter la salle, diagnostiquer l'état du serveur en direct, renommer les postes étudiants et administrer Docker sans taper de ligne de commande.

---

## ⚡ 1. Lancement Rapide de l'Application

Double-cliquez directement sur :
👉 [**`LANCER_EXAM_CONTROL.bat`**](./LANCER_EXAM_CONTROL.bat)  
*(ou lancez directement [**`ExamControlMaster.exe`**](./ExamControlMaster.exe))*

> **Temps de démarrage :** < 1 seconde.  
> **Exécution :** 100% silencieuse, aucune fenêtre noire parasite.

---

## 🐳 2. Contrôle du Serveur & Moteur Docker

- **Boutons Start et Stop Empilés (Exclusivité Mutuelle Stricte) :**
  - **`▶ DÉMARRER LE SERVEUR`** (En haut, couleur émeraude) : Lance la base PostgreSQL et le serveur FastAPI. Dès que le serveur est actif, ce bouton est automatiquement désactivé (`✔ SERVEUR DÉJÀ ACTIF`).
  - **`⏹ ARRÊTER LE SERVEUR`** (En dessous, couleur carmin) : Éteint proprement les conteneurs sans perte de données. Dès que le serveur est éteint, ce bouton est automatiquement désactivé (`⏹ SERVEUR DÉJÀ ARRÊTÉ`).
  - **Protection contre les conflits :** Pendant toute action de démarrage, d'arrêt ou de chargement d'image, les deux boutons sont verrouillés simultanément (`⏳ Action en cours...`) avec une barre de progression animée.

- **Moniteur d'Activité en Direct :**
  - Un bandeau dynamique et un mini-journal affichent en temps réel l'avancement précis de chaque opération (décompression de l'image de 125 Mo, temps écoulé, état d'écoute du port 8000).
  - Élimination totale des clignotements "Docker ON / OFF" grâce au filtre de stabilité et à l'inspection intelligente des processus Windows.

- **Actions complémentaires :**
  - **`🔄 Redémarrer`** : Relance les conteneurs à chaud.
  - **`📥 Importer .tar`** : Charge l'archive hors-ligne [`images_docker/examination-quiz-server.tar`](./images_docker/examination-quiz-server.tar) depuis une clé USB.

---

## 📡 3. Affichage Géant de l'Adresse IP & Renommage du Nom de Domaine

- **Carte Hero IP (Tableau de Bord) :**
  - Affiche l'adresse IP du serveur en gros caractères bien lisibles au tableau (ex: `192.168.1.69:8000`).
  - Détecte et sélectionne l'interface réseau active (câble Ethernet de la salle ou Wi-Fi).
  - Boutons de copie rapide : `Copier IP Seule` (`192.168.1.69`), `Copier URL Complète` (`http://192.168.1.69:8000`) et `Tester`.
- **Personnalisation Dynamique du Nom de Domaine (mDNS) :**
  - Dans l'onglet **"🔗 Accès Convivial (Nom & IP)"**, modifiez le nom d'accès en direct (ex: `quiz`, `exam`, `concours-2026`).
  - La re-diffusion sur le réseau local est instantanée sans redémarrer le serveur.
  - Le nom choisi est mémorisé et répercuté automatiquement sur le script USB `installer_nom_local.bat`.

---

## 🛡️ 4. Sauvegarde 1-Clic (Snapshots) & Pare-Feu Windows
## 🛡️ 4. Sauvegarde 1-Clic, Pare-Feu Windows & Réseau Câblé (LAN)

- **Point de Restauration Instantané (Snapshot 1-Clic) :**
  - Cliquez sur **`📸 Créer Snapshot Base`** sur le tableau de bord pour créer une sauvegarde intégrale horodatée de la base de données PostgreSQL 16 dans `backups/snapshots/` avant de lancer une épreuve.
- **Déblocage Automatique du Pare-Feu Windows :**
  - Dans l'onglet **"🩺 Diagnostic & Résolution"**, l'application vérifie si Windows Defender Firewall autorise le port 8000 (FastAPI) et 5353 (mDNS).
  - Un bouton **`Résoudre`** en 1 clic crée automatiquement les règles d'autorisation entrantes.

- **🚀 Déblocage Automatique du Réseau Câblé (Switch 100% Ethernet sans Wi-Fi) :**
  - **Problème fréquent :** Lorsque le serveur est relié par câble Ethernet à un commutateur (switch) autonome sans box/routeur Internet, Windows classe la connexion en *"Réseau Non Identifié (Public)"*. Le Pare-Feu Windows bloque alors **toutes** les requêtes entrantes des postes étudiants.
  - **Résolution 1-Clic dans l'application :** 
    - Un bandeau **"🔌 Câble LAN (Ethernet)"** indique en direct le statut (Réseau Privé ou Public).
    - Cliquez sur **`🚀 Débloquer Accès Câblé (LAN)`** : l'application bascule le profil réseau en Privé, ouvre les ports 8000 (TCP), 5353 (UDP mDNS) et autorise le Ping (ICMP) sur tous les profils de pare-feu, et configure le pont WSL2 PortProxy (`0.0.0.0:8000 -> 127.0.0.1:8000`).
  - **Résolution par script :**
    - Vous pouvez aussi faire un clic droit sur 👉 [**`debloquer_acces_lan.bat`**](./debloquer_acces_lan.bat) > *"Exécuter en tant qu'administrateur"*.
  - **⚠️ Cas d'un switch sans serveur DHCP (Adresses APIPA 169.254.x.x) :**
    - Si l'IP affichée commence par `169.254...`, il n'y a pas de serveur DHCP dans la salle. Attribuez une IP fixe au serveur (ex: `192.168.1.100`, masque `255.255.255.0`) et aux postes étudiants (`192.168.1.101`, etc.) dans les paramètres de la carte Ethernet.

---

## 🌐 5. Cartographie Réseau & Renommage des Postes (Approche 1)

1. Rendez-vous dans l'onglet **"🌐 Cartographie Réseau & Renommage"**.
2. Cliquez sur **"🔍 Lancer le Scan Réseau"** : en 0.1 seconde, l'application détecte tous les PC connectés au réseau de la salle (adresses IP, adresses MAC, latence et statut en direct).
3. **Barre de recherche instantanée :** Filtrez la liste en temps réel par IP, MAC ou Nom.
4. **Renommer un poste :** Cliquez sur le bouton **`Renommer`** pour lui donner un nom convivial (ex: *"Poste 01"*, *"Rangée A - Table 2"*).
5. Vos étiquettes sont automatiquement sauvegardées dans `data/network_topology.json`.
6. Importez ou exportez vos plans de salle via les boutons **`📥 Exporter CSV`** et **`📤 Importer CSV`** (modèle : [`plan_salle_template.csv`](./plan_salle_template.csv)).

---

## 🔑 6. Répertoire Complet des Identifiants (Logins)

Les identifiants complets sont disponibles dans [`logins.txt`](./logins.txt) et [`identifiants/logins.txt`](./identifiants/logins.txt) :

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

## 📂 6. Fichiers d'Injection d'Examens et Données Inclus

- **`csv_utilisateurs/enseignants_modules.csv`** : Fichier modèle des enseignants et de leurs modules.
- **`csv_utilisateurs/etudiants_4_specialites.csv`** : Fichier modèle des étudiants à importer.
- **`examens_json/examen_modele_python_avance.json`** : Modèle d'examen officiel Python.
- **`examens_json/examen_modele_linux.json`** : Modèle d'examen officiel Linux.
- **`examens_json/examen_modele_crypto.json`** : Modèle d'examen officiel Cryptographie.
- **`backups/all_exams_backup.json`** : Sauvegarde intégrale des épreuves.

### Comment injecter ces examens ?
Depuis votre navigateur (bouton **`🌐 Ouvrir dans le Navigateur`**) :
1. Connectez-vous avec l'enseignant responsable (ex: `prof_python`).
2. Allez dans le menu **"Créer / Importer une Épreuve"**.
3. Sélectionnez le fichier JSON souhaité dans le dossier `examens_json/`. L'examen est injecté avec l'ensemble des questions, énoncés LaTeX et tests cachés.

