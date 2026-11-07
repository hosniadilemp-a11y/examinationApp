================================================================================
   GUIDE DE DEPLOIEMENT WINDOWS SERVER — PLATEFORME D'EXAMEN & D'EVALUATION
================================================================================

1. DEMARRAGE RAPIDE EN 1 CLIC
--------------------------------------------------------------------------------
Pour lancer le serveur sous Windows :
   Double-cliquez sur "start_server.bat"

Pour arreter le serveur :
   Double-cliquez sur "stop_server.bat"

Acces Web :
   http://localhost:8000  ou  http://exam.local:8000


2. CHARGEMENT HORS-LIGNE DE L'IMAGE DOCKER (CLE USB)
--------------------------------------------------------------------------------
Si votre serveur n'a pas Internet, chargez l'image officielle fournie :
   Double-cliquez sur "load_offline_image.bat"


3. SCRIPT DE REDIRECTION ETUDIANT (exam.local)
--------------------------------------------------------------------------------
Pour que les etudiants tapent "http://exam.local:8000" :
   Copiez "installer_nom_local.bat" sur cle USB et executez-le sur chaque PC etudiant.


4. IDENTIFIANTS OFFICIELS DE CONNEXION (LOGINS)
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


5. FICHIERS DE DONNEES & EXAMENS INCLUS
--------------------------------------------------------------------------------
- csv_utilisateurs/enseignants_modules.csv  : Affectation Enseignants -> Modules
- csv_utilisateurs/etudiants_4_specialites.csv : Liste des 16 etudiants
- examens_json/examen_modele_python_avance.json : Epreuve Python
- examens_json/examen_modele_linux.json : Epreuve Linux
- examens_json/examen_modele_crypto.json : Epreuve Cryptographie
- backups/all_exams_backup.json : Sauvegarde complete JSON


6. REINITIALISER LA BASE AVEC CES DONNEES
--------------------------------------------------------------------------------
Double-cliquez sur :
   init_test_db.bat
================================================================================

