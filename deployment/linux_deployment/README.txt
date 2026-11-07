================================================================================
   GUIDE DE DEPLOIEMENT LINUX — PLATEFORME D'EXAMEN & D'EVALUATION (AUTONOME)
================================================================================

1. DEMARRAGE RAPIDE
--------------------------------------------------------------------------------
Pour demarrer la plateforme sur Linux :
   chmod +x *.sh
   ./start_server.sh

Arret du serveur :
   ./stop_server.sh

Acces Web :
   http://localhost:8000  ou  http://<IP_SERVEUR>:8000


2. CHARGEMENT HORS-LIGNE DE L'IMAGE DOCKER (CLE USB)
--------------------------------------------------------------------------------
Si la machine est hors-ligne, chargez l'image Docker binaire incluse :
   docker load -i images_docker/examination-quiz-server.tar
   docker compose up -d


3. IDENTIFIANTS OFFICIELS DE CONNEXION (LOGINS)
--------------------------------------------------------------------------------
A. ADMINISTRATEUR GLOBAL :
   Identifiant  : admin
   Mot de passe : admin123

B. ENSEIGNANTS PAR MODULE :
   - Python Init : prof_python  /  ProfPython1!   (Dr. Martin Laurent)
   - Crypto      : prof_crypto  /  ProfCrypto1!   (Dr. Sophie Bernard)
   - Linux Admin : prof_linux   /  ProfLinux1!    (Dr. Karim Mansouri)
   - Resp. Peda  : prof_martin  /  prof123        (Tous modules)

C. ETUDIANTS (16 Comptes repartis sur 4 specialites) :
   - DEV-IA      : etu_dev1, etu_dev2, etu_dev3, etu_dev4  (Mdp: StudentDev1! ... 4!)
   - SYS-ADMIN   : etu_sys1, etu_sys2, etu_sys3, etu_sys4  (Mdp: StudentSys1! ... 4!)
   - CYBER-SEC   : etu_sec1, etu_sec2, etu_sec3, etu_sec4  (Mdp: StudentSec1! ... 4!)
   - GENIE LOG.  : etudiant1, etu_log2, etu_log3, etu_log4 (Mdp: etu123, StudentLog2! ... 4!)


4. FICHIERS DE DONNEES & EXAMENS INCLUS
--------------------------------------------------------------------------------
- csv_utilisateurs/enseignants_modules.csv  : Affectation Enseignants -> Modules
- csv_utilisateurs/etudiants_4_specialites.csv : Liste des 16 etudiants
- examens_json/examen_modele_python_avance.json : Epreuve Python
- examens_json/examen_modele_linux.json : Epreuve Linux
- examens_json/examen_modele_crypto.json : Epreuve Cryptographie
- backups/all_exams_backup.json : Sauvegarde complete JSON


5. REINITIALISER LA BASE AVEC CES DONNEES
--------------------------------------------------------------------------------
Executez simplement :
   ./init_test_db.sh
================================================================================

