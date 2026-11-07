================================================================================
   GUIDE APPLICATION DESKTOP — EXAM CONTROL MASTER (SURVEILLANCE & DOCKER)
================================================================================

1. LANCEMENT DE L'APPLICATION
--------------------------------------------------------------------------------
Double-cliquez sur "LANCER_EXAM_CONTROL.bat"
(ou lancez directement "ExamControlMaster.exe")

Temps de demarrage : < 1 seconde.
Lancement totalement silencieux (aucune fenetre console noire).


2. GESTION DOCKER DEPUIS L'APPLICATION
--------------------------------------------------------------------------------
- Boutons Start et Stop empiles verticalement (exclusivite mutuelle stricte) :
  * "DEMARRER LE SERVEUR" (Haut, Vert) : actif si le serveur est arrete.
  * "ARRETER LE SERVEUR" (Bas, Rouge) : actif si le serveur est en ligne.
  * Pendant une action (demarrage, arret, chargement), les deux boutons sont
    verrouilles simultanement pour eviter toute collision.
- Moniteur d'activite et diagnostic en direct : affiche les etapes exactes
  (decompression image 125 Mo, temps ecoule, initialisation des conteneurs).
- Elimination des clignotements Docker grace au filtre de stabilite.
- Bouton "Importer .tar" pour charger l'image hors-ligne depuis une cle USB.


3. AFFICHAGE IP DU SERVEUR & RENOMMAGE DU DOMAINE (mDNS)
--------------------------------------------------------------------------------
- Carte Hero IP sur le tableau de bord : affiche l'IP du serveur en gros caracteres
  bien lisibles au tableau (ex: 192.168.1.69:8000).
- Selecteur de carte reseau : choisissez entre le cable Ethernet ou le Wi-Fi.
- Boutons de copie rapide : "Copier IP Seule" et "Copier URL Complete".
- Renommage dynamique du domaine dans l'onglet "Acces Convivial" : changez le nom
  a chaud (ex: "quiz.local", "epreuve.local") sans redemarrer le serveur.
- Fichier batch de secours genere automatiquement avec le bon nom sur cle USB.


4. SAUVEGARDE 1-CLIC (SNAPSHOTS) & PARE-FEU WINDOWS
--------------------------------------------------------------------------------
- Bouton "Creer Snapshot Base" : cree un point de restauration complet horodate
  de la base PostgreSQL 16 dans backups/snapshots/ avant de lancer une epreuve.
- Diagnostic Pare-Feu Windows : detecte si les ports 8000 (TCP) et 5353 (UDP mDNS)
  sont ouverts et offre un bouton "Resoudre" en 1 clic.


5. CARTOGRAPHIE RESEAU & NOMMAGE DES POSTES (APPROCHE 1)
--------------------------------------------------------------------------------
- Allez dans l'onglet "Cartographie Reseau" et cliquez sur "Lancer le Scan Reseau".
- Tous les PC de la salle sont detectes en 0.1s avec leur IP, MAC et latence.
- Barre de recherche instantanee pour filtrer par IP, MAC ou Nom de poste.
- Cliquez sur "Renommer" pour attribuer un nom ("Poste 01", "Table A-02").
- Exportez ou importez vos plans via les boutons CSV.


6. IDENTIFIANTS OFFICIELS DE CONNEXION (LOGINS)
--------------------------------------------------------------------------------
A. ADMINISTRATEUR GLOBAL :
   Identifiant  : admin
   Mot de passe : admin123

B. ENSEIGNANTS PAR MODULE :
   - Python Init : prof_python  /  ProfPython1!   (Dr. Martin Laurent)
   - Crypto      : prof_crypto  /  ProfCrypto1!   (Dr. Sophie Bernard)
   - Linux Admin : prof_linux   /  ProfLinux1!    (Dr. Karim Mansouri)
   - Resp. Peda  : prof_martin  /  prof123        (Tous modules)

C. ETUDIANTS (16 Comptes sur 4 specialites) :
   - DEV-IA      : etu_dev1, etu_dev2, etu_dev3, etu_dev4  (Mdp: StudentDev1! ... 4!)
   - SYS-ADMIN   : etu_sys1, etu_sys2, etu_sys3, etu_sys4  (Mdp: StudentSys1! ... 4!)
   - CYBER-SEC   : etu_sec1, etu_sec2, etu_sec3, etu_sec4  (Mdp: StudentSec1! ... 4!)
   - GENIE LOG.  : etudiant1, etu_log2, etu_log3, etu_log4 (Mdp: etu123, StudentLog2! ... 4!)


6. FICHIERS D'INJECTION D'EXAMENS ET DONNEES INCLUS
--------------------------------------------------------------------------------
- examens_json/examen_modele_python_avance.json : Epreuve Python
- examens_json/examen_modele_linux.json : Epreuve Linux
- examens_json/examen_modele_crypto.json : Epreuve Cryptographie
- csv_utilisateurs/enseignants_modules.csv : Affectation Enseignants -> Modules
- csv_utilisateurs/etudiants_4_specialites.csv : Liste des 16 etudiants
================================================================================

