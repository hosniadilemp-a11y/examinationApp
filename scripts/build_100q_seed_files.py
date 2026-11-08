import os
import json

def build_seeds():
    seeds_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app", "seeds")
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "app", "data")

    # --------------------------------------------------------------------------
    # 1. PROGRAMMATION PYTHON (100 Questions) = Algo (30) + Python (30) + 40 Curriculum
    # --------------------------------------------------------------------------
    with open(os.path.join(seeds_dir, "seed_algo_30.json"), "r", encoding="utf-8") as f:
        algo_30 = json.load(f)
    with open(os.path.join(seeds_dir, "seed_python_30.json"), "r", encoding="utf-8") as f:
        py_30 = json.load(f)

    with open(os.path.join(data_dir, "python_training", "curriculum.json"), "r", encoding="utf-8") as f:
        py_curr = json.load(f)

    py_100 = []
    # Add first 30 Algo questions
    for idx, q in enumerate(algo_30, start=1):
        q_copy = dict(q)
        q_copy["ordering"] = idx
        py_100.append(q_copy)

    # Add next 30 Python questions
    for idx, q in enumerate(py_30, start=31):
        q_copy = dict(q)
        q_copy["ordering"] = idx
        py_100.append(q_copy)

    # Collect 40 diverse questions from Python curriculum across chapters 0 to 9
    collected_py = []
    seen_prompts = {q["prompt_markdown"] for q in py_100}
    for chap in py_curr.get("chapters", []):
        for raw_q in chap.get("mcq_questions", []):
            prompt = (raw_q.get("text") or "").strip()
            if not prompt or prompt in seen_prompts:
                continue
            seen_prompts.add(prompt)
            opts = raw_q.get("options", [])
            corr = raw_q.get("correct", [0])
            if not opts or not isinstance(corr, list) or len(corr) == 0:
                continue

            opts_formatted = []
            for o_idx, opt_text in enumerate(opts[:5]):
                opts_formatted.append({"id": chr(97 + o_idx), "text": str(opt_text)})

            corr_ids = [chr(97 + c) for c in corr if c < len(opts_formatted)]
            if not corr_ids:
                continue

            q_type = "single_choice" if len(corr_ids) == 1 else "multi_choice"
            final_corr = corr_ids[0] if q_type == "single_choice" else corr_ids

            collected_py.append({
                "ordering": len(py_100) + len(collected_py) + 1,
                "type": q_type,
                "prompt_markdown": prompt,
                "points": float(raw_q.get("points", 1.0)),
                "negative_penalty": float(raw_q.get("penalty", 0.5)),
                "options_json": json.dumps(opts_formatted, ensure_ascii=False),
                "correct_answers_json": json.dumps(final_corr, ensure_ascii=False),
                "explanation": raw_q.get("explanation", "")
            })
            if len(collected_py) >= 40:
                break
        if len(collected_py) >= 40:
            break

    py_100.extend(collected_py)
    assert len(py_100) == 100, f"Expected 100 questions for PYTHON_PROG, got {len(py_100)}"

    # --------------------------------------------------------------------------
    # 2. SYSTÈMES D'EXPLOITATION (100 Questions) = Linux 30 + 70 Linux Curriculum
    # --------------------------------------------------------------------------
    with open(os.path.join(seeds_dir, "seed_linux_30.json"), "r", encoding="utf-8") as f:
        linux_30 = json.load(f)

    with open(os.path.join(data_dir, "linux_training", "curriculum.json"), "r", encoding="utf-8") as f:
        lin_curr = json.load(f)

    sys_100 = []
    for idx, q in enumerate(linux_30, start=1):
        q_copy = dict(q)
        q_copy["ordering"] = idx
        sys_100.append(q_copy)

    collected_lin = []
    seen_lin_prompts = {q["prompt_markdown"] for q in sys_100}
    for chap in lin_curr.get("chapters", []):
        for raw_q in chap.get("mcq_questions", []):
            prompt = (raw_q.get("prompt") or raw_q.get("text") or "").strip()
            if not prompt or prompt in seen_lin_prompts:
                continue
            seen_lin_prompts.add(prompt)
            raw_opts = raw_q.get("options", [])
            raw_corr = raw_q.get("correct", 0)
            if not isinstance(raw_opts, list) or len(raw_opts) < 2:
                continue

            opts_formatted = []
            for o_idx, opt in enumerate(raw_opts[:5]):
                opt_text = opt.get("text") if isinstance(opt, dict) else str(opt)
                opts_formatted.append({"id": chr(97 + o_idx), "text": opt_text})

            if isinstance(raw_corr, list):
                corr_indices = raw_corr
            elif isinstance(raw_corr, int):
                corr_indices = [raw_corr]
            else:
                corr_indices = [0]

            corr_ids = [chr(97 + c) for c in corr_indices if c < len(opts_formatted)]
            if not corr_ids:
                continue

            q_type = "single_choice" if len(corr_ids) == 1 else "multi_choice"
            final_corr = corr_ids[0] if q_type == "single_choice" else corr_ids

            collected_lin.append({
                "ordering": len(sys_100) + len(collected_lin) + 1,
                "type": q_type,
                "prompt_markdown": prompt,
                "points": float(raw_q.get("points", 1.0)),
                "negative_penalty": float(raw_q.get("penalty", 0.5)),
                "options_json": json.dumps(opts_formatted, ensure_ascii=False),
                "correct_answers_json": json.dumps(final_corr, ensure_ascii=False),
                "explanation": raw_q.get("explanation", "")
            })
            if len(collected_lin) >= 70:
                break
        if len(collected_lin) >= 70:
            break

    sys_100.extend(collected_lin)
    assert len(sys_100) == 100, f"Expected 100 questions for SYS_EXPLOIT, got {len(sys_100)}"

    # --------------------------------------------------------------------------
    # 3. CYBERSÉCURITÉ & CRYPTOGRAPHIE (100 Questions) = Crypto 30 + 70 Questions Curated
    # --------------------------------------------------------------------------
    with open(os.path.join(seeds_dir, "seed_crypto_30.json"), "r", encoding="utf-8") as f:
        crypto_30 = json.load(f)

    cyber_100 = []
    for idx, q in enumerate(crypto_30, start=1):
        q_copy = dict(q)
        q_copy["ordering"] = idx
        cyber_100.append(q_copy)

    # 70 Curated professional questions in Cryptography and Cybersecurity
    curated_cyber = [
        # 1. Symmetric Cryptography
        {
            "prompt": "Quel algorithme de chiffrement symétrique par blocs est le standard mondial adopté par le NIST pour succéder au DES ?",
            "opts": ["AES (Rijndael)", "Blowfish", "RC4", "Twofish"],
            "corr": "a",
            "expl": "L'AES (Advanced Encryption Standard), basé sur l'algorithme Rijndael avec des blocs de 128 bits, est le standard officiel."
        },
        {
            "prompt": "Quelle est la taille de bloc standard (en bits) utilisée par l'algorithme AES, quelle que soit la longueur de la clé ?",
            "opts": ["128 bits", "64 bits", "256 bits", "512 bits"],
            "corr": "a",
            "expl": "AES traite obligatoirement des blocs de 128 bits, avec des clés de 128, 192 ou 256 bits."
        },
        {
            "prompt": "Quelle est la principale faiblesse du mode de chiffrement ECB (Electronic Codebook) ?",
            "opts": [
                "Deux blocs de texte en clair identiques produisent des blocs chiffrés identiques",
                "Il ne supporte pas les clés de 256 bits",
                "Il nécessite obligatoirement un échange asymétrique",
                "Il requiert une synchronisation temporelle stricte"
            ],
            "corr": "a",
            "expl": "Le mode ECB ne masque pas les redondances et les motifs du texte clair, ce qui rend le chiffré analysable visuellement ou statistiquement."
        },
        {
            "prompt": "Quel mode d'opération de chiffrement symétrique fournit simultanément la confidentialité et l'intégrité authentifiée des données (AEAD) ?",
            "opts": ["GCM (Galois/Counter Mode)", "ECB (Electronic Codebook)", "CBC classique", "OFB (Output Feedback)"],
            "corr": "a",
            "expl": "AES-GCM est un mode AEAD moderne très rapide combinant le chiffrement CTR et une étiquette d'authentification GMAC."
        },
        {
            "prompt": "Dans le chiffrement symétrique en mode CBC, quel est le rôle du Vecteur d'Initialisation (IV) ?",
            "opts": [
                "Garantir qu'un même texte clair chiffré deux fois produise des cryptogrammes distincts",
                "Remplacer la clé secrète partagée",
                "Signer numériquement le message",
                "Compresser le texte clair avant chiffrement"
            ],
            "corr": "a",
            "expl": "L'IV doit être aléatoire ou pseudo-aléatoire et unique pour éviter que des messages commençant de la même façon ne révèlent des similitudes."
        },
        {
            "prompt": "Pourquoi l'algorithme de chiffrement à flot RC4 est-il aujourd'hui totalement banni des protocoles modernes comme TLS 1.3 ?",
            "opts": [
                "Des biais statistiques dans les premiers octets du flux permettent de recouvrer le texte clair",
                "Il n'utilise que des opérations 8 bits incompatibles avec les processeurs 64 bits",
                "Sa licence propriétaire interdit l'usage public",
                "Il nécessite obligatoirement du matériel quantique"
            ],
            "corr": "a",
            "expl": "RC4 présente de sérieux biais dans son générateur pseudo-aléatoire (attaques Fluhrer-Mantin-Shamir, Bar-mitzvah, etc.)."
        },
        {
            "prompt": "Selon le principe de Kerckhoffs, la sécurité d'un système cryptographique doit reposer uniquement sur :",
            "opts": [
                "Le secret de la clé cryptographique, l'algorithme pouvant être public",
                "Le secret absolu de l'algorithme et de son implémentation",
                "La complexité de l'infrastructure réseau",
                "L'absence totale de documentation technique"
            ],
            "corr": "a",
            "expl": "Le principe de Kerckhoffs stipule que la sécurité d'un cryptosystème ne doit dépendre que du secret de la clé, jamais de la confidentialité de l'algorithme."
        },

        # 2. Asymmetric Cryptography
        {
            "prompt": "Sur quel problème mathématique réputé difficile repose la sécurité du cryptosystème asymétrique RSA ?",
            "opts": [
                "La factorisation d'entiers produit de deux grands nombres premiers",
                "Le logarithme discret sur champ fini uniquement",
                "Le sac à dos (Knapsack problem)",
                "Le voyageur de commerce (TSP)"
            ],
            "corr": "a",
            "expl": "RSA tire sa sécurité de la difficulté de factoriser n = p * q lorsque p et q sont de très grands nombres premiers."
        },
        {
            "prompt": "Quel est le principal avantage de la cryptographie sur les courbes elliptiques (ECC) par rapport à RSA ?",
            "opts": [
                "Offrir un niveau de sécurité équivalent avec des tailles de clés beaucoup plus courtes",
                "Ne nécessiter aucun calcul modulaire",
                "Être totalement insensible aux attaques par ordinateur quantique",
                "Supprimer le besoin d'autorités de certification"
            ],
            "corr": "a",
            "expl": "Une clé ECC de 256 bits offre un niveau de sécurité comparable à une clé RSA de 3072 bits, réduisant la consommation de bande passante et de calcul."
        },
        {
            "prompt": "Dans le protocole d'échange de clés Diffie-Hellman classique, quel problème fondamental n'est PAS résolu nativement sans authentification ?",
            "opts": [
                "L'attaque de l'homme du milieu (Man-in-the-Middle)",
                "Le calcul modulaire de la puissance",
                "La dérivation de clé symétrique",
                "L'accord sur les paramètres p et g"
            ],
            "corr": "a",
            "expl": "Diffie-Hellman pur ne fournit pas d'authentification des parties, le rendant vulnérable à une attaque MitM sans certificat ou signature."
        },
        {
            "prompt": "Lorsqu'Alice souhaite envoyer un message confidentiel à Bob avec un cryptosystème asymétrique, quelle clé utilise-t-elle pour chiffrer le message ?",
            "opts": [
                "La clé publique de Bob",
                "La clé privée d'Alice",
                "La clé publique d'Alice",
                "La clé privée de Bob"
            ],
            "corr": "a",
            "expl": "Alice chiffre avec la clé publique du destinataire (Bob), et seul Bob pourra le déchiffrer à l'aide de sa clé privée correspondante."
        },
        {
            "prompt": "Lorsqu'Alice signe numériquement un document pour prouver son authenticité et sa non-répudiation, quelle clé utilise-t-elle ?",
            "opts": [
                "Sa propre clé privée",
                "La clé publique de Bob",
                "La clé publique de l'autorité de certification",
                "Une clé symétrique partagée"
            ],
            "corr": "a",
            "expl": "Alice chiffre l'empreinte de hachage avec sa clé privée ; quiconque possédant sa clé publique peut vérifier l'intégrité et l'authenticité."
        },

        # 3. Hash Functions and Integrity
        {
            "prompt": "Quelle propriété d'une fonction de hachage cryptographique garantit qu'il est impossible de trouver deux messages distincts produisant la même empreinte ?",
            "opts": [
                "Résistance aux collisions",
                "Résistance à la première préimage",
                "Résistance à la seconde préimage",
                "Effet avalanche"
            ],
            "corr": "a",
            "expl": "La résistance aux collisions stipule qu'il est impossible en pratique de trouver deux entrées x1 != x2 telles que H(x1) = H(x2)."
        },
        {
            "prompt": "Quelle est la taille en bits du condensat (hash digest) généré par la fonction SHA-256 ?",
            "opts": ["256 bits (32 octets)", "128 bits (16 octets)", "512 bits (64 octets)", "160 bits (20 octets)"],
            "corr": "a",
            "expl": "SHA-256 génère une empreinte numérique de 256 bits, soit 32 octets, généralement représentée par 64 caractères hexadécimaux."
        },
        {
            "prompt": "Pourquoi les fonctions MD5 et SHA-1 sont-elles formellement déconseillées pour signer des certificats numériques ?",
            "opts": [
                "Des collisions pratiques ont été démontrées et générées en laboratoire",
                "Leur calcul consomme trop de mémoire vive",
                "Elles sont incompatibles avec le codage UTF-8",
                "Elles nécessitent des clés privées trop volumineuses"
            ],
            "corr": "a",
            "expl": "Des attaques par collision pratiques (ex: SHAttered pour SHA-1, Flame pour MD5) ont démontré leur rupture cryptographique définitive."
        },
        {
            "prompt": "Quel mécanisme cryptographique permet de vérifier à la fois l'intégrité et l'authenticité d'un message en combinant une fonction de hachage et une clé secrète ?",
            "opts": ["HMAC (Hash-based Message Authentication Code)", "CRC32", "Base64", "MD5 simple"],
            "corr": "a",
            "expl": "HMAC combine une clé secrète partagée et une fonction de hachage cryptographique pour produire un tag d'intégrité infalsifiable."
        },

        # 4. PKI and Certificates
        {
            "prompt": "Dans une infrastructure à clés publiques (PKI), quel document standard définit le format des certificats numériques électroniques ?",
            "opts": ["X.509", "RFC 1918", "IEEE 802.11", "ISO 27001"],
            "corr": "a",
            "expl": "La norme ITU-T X.509 régit la structure, les attributs et les signatures des certificats de clés publiques."
        },
        {
            "prompt": "Quel protocole moderne et léger permet à un client de vérifier en temps réel le statut de révocation d'un certificat sans télécharger l'intégralité de la CRL ?",
            "opts": ["OCSP (Online Certificate Status Protocol)", "SNMP", "NTP", "BGP"],
            "corr": "a",
            "expl": "OCSP permet d'interroger directement un répondeur pour connaître l'état (valide, révoqué, inconnu) d'un certificat spécifique."
        },
        {
            "prompt": "Quelle extension du protocole TLS permet à un serveur de présenter lui-même une réponse de révocation OCSP signée et horodatée par la CA lors du handshake ?",
            "opts": ["OCSP Stapling", "SNI (Server Name Indication)", "ALPN", "STARTTLS"],
            "corr": "a",
            "expl": "L'OCSP Stapling (agrafage OCSP) évite que chaque client n'interroge le serveur de la CA, améliorant les performances et la confidentialité."
        },
        {
            "prompt": "Qu'est-ce qu'une attaque par certificat révoqué ou expiré ignorée dans une application ?",
            "opts": [
                "Une brèche permettant l'interception et le déchiffrement des flux par usurpation d'identité (MitM)",
                "Une panne matérielle du processeur hôte",
                "Un dépassement de tampon sur la carte réseau",
                "Une boucle de routage au niveau IP"
            ],
            "corr": "a",
            "expl": "Désactiver la vérification des certificats ou ignorer leur expiration permet à un attaquant en position d'écoute de falsifier l'identité du serveur."
        },

        # 5. Password Security & KDF
        {
            "prompt": "Pourquoi le simple hachage d'un mot de passe avec SHA-256 est-il insuffisant pour le stockage sécurisé dans une base de données ?",
            "opts": [
                "SHA-256 est trop rapide, facilitant les attaques par force brute et dictionnaires sur GPU",
                "SHA-256 est réversible avec une clé publique",
                "SHA-256 tronque les mots de passe de plus de 8 caractères",
                "SHA-256 génère obligatoirement des collisions"
            ],
            "corr": "a",
            "expl": "Les fonctions de hachage généralistes sont conçues pour être ultrarapides. Sur GPU moderne, des milliards de hash SHA-256 peuvent être calculés par seconde."
        },
        {
            "prompt": "Quel est le rôle fondamental du 'sel' (salt) cryptographique aléatoire associé à chaque mot de passe lors de son enregistrement ?",
            "opts": [
                "Empêcher l'efficacité des tables arc-en-ciel (rainbow tables) et la détection de doublons",
                "Chiffrer le mot de passe de façon réversible",
                "Vérifier la validité de l'adresse email de l'utilisateur",
                "Augmenter artificiellement la bande passante réseau"
            ],
            "corr": "a",
            "expl": "Le sel garantit que deux utilisateurs ayant le même mot de passe auront des hachés totalement différents, rendant les tables précalculées inutilisables."
        },
        {
            "prompt": "Quel algorithme de dérivation de clé (KDF) a remporté la Password Hashing Competition (PHC) et est réputé résistant aux attaques par matériel dédié (ASIC/GPU) ?",
            "opts": ["Argon2 (Argon2id)", "MD5-Crypt", "SHA-512", "HMAC-MD5"],
            "corr": "a",
            "expl": "Argon2id est le standard recommandé par l'OWASP, configuré avec des paramètres de coût en temps, en mémoire vive et en parallélisme."
        },
        {
            "prompt": "Qu'est-ce qu'un 'poivre' (pepper) dans le contexte de la sécurité des mots de passe ?",
            "opts": [
                "Une valeur secrète globale stockée hors de la base de données (ex: HSM ou variable d'env) ajoutée avant hachage",
                "Un algorithme de hachage obsolète",
                "Une liste de mots de passe interdits",
                "Un cookie d'authentification temporaire"
            ],
            "corr": "a",
            "expl": "Le poivre ajoute une couche de protection : même en cas de fuite de la base de données SQL, l'attaquant ne dispose pas du secret nécessaire pour recalculer les hachés."
        },

        # 6. Web & Application Security (OWASP)
        {
            "prompt": "Quelle vulnérabilité survient lorsqu'une application inclut des données non fiables dans une page web sans échappement, exécutant du code JavaScript dans le navigateur victime ?",
            "opts": ["XSS (Cross-Site Scripting)", "SQLi (Injection SQL)", "CSRF", "SSRF"],
            "corr": "a",
            "expl": "Le Cross-Site Scripting (XSS) permet à un pirate de dérober des cookies de session, détourner le compte de l'utilisateur ou injecter de fausses interfaces."
        },
        {
            "prompt": "Quelle mesure technique est la protection la plus universelle et rigoureuse contre les attaques par injection SQL ?",
            "opts": [
                "L'utilisation systématique de requêtes préparées avec requêtes paramétrées (Prepared Statements / ORM)",
                "Le filtrage artisanal des mots-clés 'SELECT' et 'UNION'",
                "Le chiffrement symétrique de toute la base de données",
                "L'interdiction des espaces dans les champs de saisie"
            ],
            "corr": "a",
            "expl": "Les requêtes préparées séparent formellement la structure du code SQL et les données d'entrée fournies par l'utilisateur."
        },
        {
            "prompt": "Quel attribut de cookie HTTP empêche le code JavaScript côté client (y compris lors d'une attaque XSS) d'accéder au cookie de session ?",
            "opts": ["HttpOnly", "Secure", "SameSite", "Domain"],
            "corr": "a",
            "expl": "L'attribut HttpOnly interdit tout accès au cookie via document.cookie, neutralisant le vol de session direct par script malveillant."
        },
        {
            "prompt": "Quel attribut de cookie permet de restreindre l'envoi de cookies lors des requêtes d'origine croisée pour neutraliser les attaques CSRF ?",
            "opts": ["SameSite=Strict ou SameSite=Lax", "HttpOnly", "Secure", "Path=/"],
            "corr": "a",
            "expl": "SameSite empêche le navigateur d'envoyer le cookie avec des requêtes initiées par des sites tiers, contrecarrant le CSRF."
        },
        {
            "prompt": "Quelle vulnérabilité consiste pour un serveur à exécuter des requêtes HTTP vers des ressources internes protégées sur instruction non validée d'un utilisateur ?",
            "opts": ["SSRF (Server-Side Request Forgery)", "CSRF", "XSS", "Clickjacking"],
            "corr": "a",
            "expl": "Le SSRF permet à un pirate d'utiliser le serveur cible comme relais pour sonder le réseau local interne, les services de métadonnées cloud (169.254.169.254), etc."
        },
        {
            "prompt": "Qu'est-ce qu'une faille IDOR (Insecure Direct Object Reference) ?",
            "opts": [
                "L'accès non autorisé à un objet ou enregistrement via modification directe de son identifiant (ex: /api/order/102)",
                "L'injection de requêtes DNS non sécurisées",
                "Un débordement d'entier dans un pilote graphique",
                "L'absence d'antivirus sur le poste de travail"
            ],
            "corr": "a",
            "expl": "L'IDOR se produit lorsque l'application utilise l'identifiant fourni par le client sans vérifier si l'utilisateur possède les autorisations d'accès sur cette ressource."
        },
        {
            "prompt": "Quel en-tête de réponse HTTP permet d'interdire l'affichage d'une page dans une iframe afin d'empêcher les attaques par Clickjacking ?",
            "opts": ["X-Frame-Options: DENY (ou frame-ancestors en CSP)", "X-Content-Type-Options: nosniff", "Strict-Transport-Security", "Access-Control-Allow-Origin"],
            "corr": "a",
            "expl": "X-Frame-Options ou CSP frame-ancestors empêche un site malveillant d'intégrer l'application dans une iframe invisible pour piéger les clics de la victime."
        },
        {
            "prompt": "Quel en-tête HTTP moderne permet de définir précisément quelles sources de scripts, images, polices et connexions externes le navigateur est autorisé à charger ?",
            "opts": ["Content-Security-Policy (CSP)", "CORS", "X-XSS-Protection", "ETag"],
            "corr": "a",
            "expl": "CSP (Content Security Policy) est une couche de défense majeure restreignant l'exécution de code arbitraire et atténuant grandement les failles XSS."
        },

        # 7. Network Security & Protocols
        {
            "prompt": "Quelle attaque au niveau de la couche liaison (OSI niveau 2) permet à un intrus de s'insérer entre deux machines en faussant les tables de correspondance IP/MAC ?",
            "opts": ["ARP Poisoning / ARP Spoofing", "DNS Tunneling", "BGP Hijacking", "SYN Flood"],
            "corr": "a",
            "expl": "L'usurpation ARP consiste à émettre de fausses réponses ARP pour associer l'adresse MAC de l'attaquant à l'IP d'une passerelle ou d'un serveur légitime."
        },
        {
            "prompt": "Dans une attaque par déni de service SYN Flood, quel mécanisme du protocole TCP est détourné pour épuiser les ressources du serveur ?",
            "opts": [
                "L'envoi massif de paquets SYN sans jamais renvoyer le paquet ACK final (connexions demi-ouvertes)",
                "La surcharge des trames FIN/RST",
                "La modification du numéro de port éphémère",
                "Le calcul incorrect de la somme de contrôle TCP"
            ],
            "corr": "a",
            "expl": "Le serveur alloue des structures mémoire dans sa file d'attente (backlog) pour chaque SYN reçu en attente du handshake à 3 voies qui n'arrive jamais."
        },
        {
            "prompt": "Quel mécanisme technique déployé au niveau du noyau Linux ou des pare-feux permet de contrer efficacement les attaques SYN Flood ?",
            "opts": ["SYN Cookies", "Chiffrement AES", "Désactivation du port 80", "Double NAT"],
            "corr": "a",
            "expl": "Les SYN Cookies encodent les paramètres de la connexion dans le numéro de séquence initial sans allouer d'état mémoire jusqu'à la réception du ACK."
        },
        {
            "prompt": "Quel protocole de sécurité réseau ajoute des signatures cryptographiques aux enregistrements DNS pour garantir leur authenticité et leur intégrité ?",
            "opts": ["DNSSEC (DNS Security Extensions)", "DoH (DNS over HTTPS)", "DHCP Snooping", "NTPsec"],
            "corr": "a",
            "expl": "DNSSEC empêche l'empoisonnement de cache DNS (DNS Cache Poisoning) en validant cryptographiquement l'origine des réponses."
        },
        {
            "prompt": "Quelle est la principale amélioration apportée par TLS 1.3 concernant la négociation du handshake par rapport à TLS 1.2 ?",
            "opts": [
                "Handshake réduit à 1 seul aller-retour (1-RTT) et suppression des suites cryptographiques non sécurisées",
                "Obligation d'utiliser des adresses IPv6",
                "Remplacement complet de TCP par UDP",
                "Suppression des clés privées côté serveur"
            ],
            "corr": "a",
            "expl": "TLS 1.3 accélère la connexion (1-RTT ou 0-RTT avec session resumption) tout en interdisant RSA pour l'échange de clés, forçant le Forward Secrecy."
        },
        {
            "prompt": "Que signifie la propriété cryptographique 'PFS' (Perfect Forward Secrecy / Confidentialité persistante) dans les échanges TLS ?",
            "opts": [
                "La compromission ultérieure de la clé privée à long terme du serveur ne permettra pas de déchiffrer les sessions enregistrées par le passé",
                "Le serveur n'a plus besoin de certificat numérique",
                "Le mot de passe de l'utilisateur est conservé indéfiniment sans risque",
                "Le trafic est chiffré deux fois par deux algorithmes distincts"
            ],
            "corr": "a",
            "expl": "PFS génère des clés de session éphémères (ex: ECDHE) pour chaque communication. Une fois la session close, ces clés sont définitivement détruites."
        },

        # 8. Authentication, IAM and Tokens
        {
            "prompt": "Dans le protocole TOTP (Time-based One-Time Password) utilisé pour la 2FA (RFC 6238), quels éléments sont combinés pour générer le code à 6 chiffres ?",
            "opts": [
                "Un secret partagé et l'horodatage courant divisé en fenêtres de temps (souvent 30 secondes)",
                "L'adresse MAC et l'adresse IP publique de l'utilisateur",
                "Le mot de passe de l'utilisateur et son numéro de téléphone",
                "Un compteur de clics envoyé par SMS"
            ],
            "corr": "a",
            "expl": "TOTP applique HMAC sur le timestamp courant discrétisé par tranches de 30 secondes en utilisant la clé secrète partagée lors de l'enrôlement."
        },
        {
            "prompt": "Dans un jeton JWT (JSON Web Token), quelle partie contient la signature numérique garantissant que les données n'ont pas été modifiées ?",
            "opts": [
                "La 3e partie (Header.Payload.Signature)",
                "La 1re partie uniquement",
                "La 2e partie (Payload)",
                "Le cookie de session externe"
            ],
            "corr": "a",
            "expl": "Un JWT est composé de 3 segments séparés par des points : l'en-tête (Header), le corps (Payload) et la signature cryptographique (Signature)."
        },
        {
            "prompt": "Quelle vulnérabilité critique a historiquement touché certaines implémentations naïves de vérification des jetons JWT ?",
            "opts": [
                "L'acceptation de l'algorithme 'none' dans l'en-tête, désactivant la vérification de la signature",
                "L'obligation de chiffrer l'en-tête en Base64",
                "La limitation de taille à 256 octets",
                "L'expiration automatique au bout de 5 secondes"
            ],
            "corr": "a",
            "expl": "Si la bibliothèque accepte 'alg': 'none', un attaquant peut modifier les privilèges (ex: 'admin': true) sans recalculer de signature valide."
        },
        {
            "prompt": "Dans le standard OAuth 2.0, quel est le flux (grant type) recommandé pour les applications web avec serveur backend (sécurité maximale) ?",
            "opts": [
                "Authorization Code Grant (avec PKCE)",
                "Implicit Flow",
                "Resource Owner Password Credentials",
                "Client Credentials sans authentification"
            ],
            "corr": "a",
            "expl": "L'Authorization Code Grant combiné à PKCE est le flux standard recommandé par l'IETF pour sécuriser l'échange de jetons."
        },
        {
            "prompt": "Quel protocole d'authentification réseau basé sur un centre de distribution de clés (KDC) et des tickets d'accès est le cœur des domaines Microsoft Active Directory ?",
            "opts": ["Kerberos", "RADIUS", "TACACS+", "LDAP sans chiffrement"],
            "corr": "a",
            "expl": "Kerberos (port 88) utilise un KDC (Authentication Server + Ticket Granting Server) pour authentifier les utilisateurs et services via des tickets chiffrés."
        },

        # 9. Infrastructure, Network Defense and Architecture
        {
            "prompt": "Quelle est la différence fondamentale entre un pare-feu sans état (stateless) et un pare-feu à état (stateful) ?",
            "opts": [
                "Le pare-feu stateful analyse le contexte et le suivi des connexions (table d'états TCP/UDP) au-delà des paquets individuels",
                "Le pare-feu stateless chiffre l'ensemble des paquets",
                "Le pare-feu stateful ne fonctionne qu'au niveau applicatif HTTP",
                "Le pare-feu stateless bloque obligatoirement tous les flux UDP"
            ],
            "corr": "a",
            "expl": "Un pare-feu stateful suit les sessions réseau (états NEW, ESTABLISHED, RELATED) pour autoriser automatiquement les flux retour légitimes."
        },
        {
            "prompt": "Quel équipement de sécurité réseau se distingue d'un IDS (détection) par sa capacité à bloquer activement le trafic malveillant en temps réel ?",
            "opts": ["IPS (Intrusion Prevention System)", "SIEM", "Sonde NetFlow", "Serveur Syslog"],
            "corr": "a",
            "expl": "L'IPS est positionné en coupure (inline) sur le réseau et peut abandonner immédiatement les paquets hostiles (drop) détectés."
        },
        {
            "prompt": "Qu'est-ce qu'une zone démilitarisée (DMZ) dans l'architecture réseau d'une organisation ?",
            "opts": [
                "Un sous-réseau isolé hébergeant les serveurs accessibles depuis Internet pour protéger le réseau interne",
                "Une zone sans aucune sécurité ni pare-feu",
                "Un réseau privé réservé exclusivement aux administrateurs systèmes",
                "Une base de données de secours"
            ],
            "corr": "a",
            "expl": "La DMZ sépare les services exposés (web, mail) du réseau interne confidentiel, limitant l'impact en cas de compromission d'un serveur public."
        },
        {
            "prompt": "Quel est le principe fondamental du modèle de sécurité 'Zero Trust' (Confiance Zéro) ?",
            "opts": [
                "Ne jamais faire confiance, toujours vérifier (Never Trust, Always Verify), quel que soit l'emplacement de l'utilisateur",
                "Faire confiance par défaut à tous les équipements situés sur le réseau local interne",
                "Interdire tout accès distant aux télétravailleurs",
                "Supprimer tous les mots de passe et les pare-feux"
            ],
            "corr": "a",
            "expl": "Zero Trust part du principe que des menaces existent déjà au sein du réseau et impose une vérification d'identité et de contexte continue."
        },
        {
            "prompt": "Quel outil centralise, agrège et corrèle les journaux d'événements de sécurité de l'ensemble d'un parc informatique pour détecter les incidents ?",
            "opts": ["SIEM (Security Information and Event Management)", "DHCP", "DNS Resolver", "SNMP Trap simple"],
            "corr": "a",
            "expl": "Un SIEM (comme Splunk, Elastic Security ou Wazuh) corrèle les logs de pare-feux, serveurs et postes pour générer des alertes de sécurité."
        },

        # 10. Threats, Malware & Social Engineering
        {
            "prompt": "Quel type de logiciel malveillant chiffre les données d'un système victime et exige un paiement financier pour fournir la clé de déchiffrement ?",
            "opts": ["Ransomware (Rançongiciel)", "Spyware", "Adware", "Scareware simple"],
            "corr": "a",
            "expl": "Les ransomwares (ex: WannaCry, LockBit) paralysent les organisations en chiffrant leurs sauvegardes et serveurs de production."
        },
        {
            "prompt": "Quelle technique d'ingénierie sociale consiste à cibler spécifiquement un cadre dirigeant ou une personne clé d'une organisation avec un message hyper-personnalisé ?",
            "opts": ["Spear-phishing (ou Whaling)", "Phishing de masse", "Vishing aveugle", "Spamming commercial"],
            "corr": "a",
            "expl": "Le spear-phishing (harponnage) exploite des recherches préalables poussées sur la victime pour tromper sa vigilance avec un scénario sur-mesure."
        },
        {
            "prompt": "Qu'est-ce qu'une vulnérabilité 'Zero-Day' (0-day) ?",
            "opts": [
                "Une vulnérabilité de sécurité inconnue de l'éditeur ou sans correctif de sécurité disponible",
                "Une faille vieille de plusieurs années répertoriée sur le site de l'ANSSI",
                "Une panne d'électricité générale dans un datacenter",
                "Une erreur de saisie lors de la création d'un utilisateur"
            ],
            "corr": "a",
            "expl": "Le terme Zero-Day signifie que l'éditeur dispose de zéro jour de préavis pour concevoir un patch avant qu'une exploitation ne soit possible."
        },
        {
            "prompt": "Quelle attaque consiste pour un pirate à injecter des données dépassant la mémoire allouée sur la pile (stack) afin de détourner le flot d'exécution du programme ?",
            "opts": ["Buffer Overflow (Dépassement de tampon)", "Race Condition", "Cross-Site Scripting", "XML Injection"],
            "corr": "a",
            "expl": "Le dépassement de tampon permet d'écraser l'adresse de retour (EIP/RIP) pour faire exécuter du code arbitraire (shellcode)."
        },
        {
            "prompt": "Quel mécanisme de protection au niveau du système d'exploitation rend aléatoires les adresses mémoire des bibliothèques et de la pile pour compliquer les exploits ?",
            "opts": ["ASLR (Address Space Layout Randomization)", "DEP / NX bit", "Stack Canary", "Secure Boot"],
            "corr": "a",
            "expl": "L'ASLR permute les adresses en mémoire à chaque exécution du processus, empêchant l'attaquant de cibler des adresses mémoire fixes."
        },

        # 11. Advanced Cryptanalysis & Secure Coding
        {
            "prompt": "Quel type d'attaque cryptographique exploite le temps mis par un serveur pour comparer deux chaînes de caractères (ex: signatures ou clés) ?",
            "opts": [
                "Attaque par canal auxiliaire temporelle (Timing Attack)",
                "Attaque par dictionnaire",
                "Attaque par rejeu (Replay attack)",
                "Attaque par collision SHA-3"
            ],
            "corr": "a",
            "expl": "Une attaque temporelle mesure les micro-variations de temps d'exécution pour deviner octet par octet une valeur secrète. On y pare avec du temps constant (constant-time compare)."
        },
        {
            "prompt": "Pourquoi l'utilisation d'un générateur de nombres pseudo-aléatoires standard (comme `random()` en Python) est-elle interdite pour générer des clés cryptographiques ?",
            "opts": [
                "Leur état interne est prédictible car ils sont conçus pour les simulations mathématiques, non pour la sécurité",
                "Ils ne génèrent que des nombres pairs",
                "Ils consomment trop de mémoire vive",
                "Ils dépendent exclusivement du protocole NTP"
            ],
            "corr": "a",
            "expl": "Il faut impérativement utiliser un CSPRNG (Cryptographically Secure Pseudo-Random Number Generator, ex: `secrets` ou `/dev/urandom`)."
        },
        {
            "prompt": "Dans le protocole IPsec, quel protocole fournit à la fois le chiffrement des paquets, l'authentification et l'intégrité des données ?",
            "opts": ["ESP (Encapsulating Security Payload)", "AH (Authentication Header)", "IKEv1", "GRE"],
            "corr": "a",
            "expl": "ESP assure à la fois la confidentialité (chiffrement) et l'intégrité, tandis que AH n'assure que l'intégrité sans aucun chiffrement."
        },
        {
            "prompt": "Qu'est-ce qu'une attaque par rejeu (Replay Attack) et comment s'en prémunir ?",
            "opts": [
                "L'interception d'un message légitime pour le renvoyer à l'identique ; on s'en protège avec des nonces ou horodatages stricts",
                "La modification du mot de passe utilisateur dans l'annuaire LDAP",
                "Une attaque par déni de service sur le serveur web",
                "Le reformatage complet d'un disque dur"
            ],
            "corr": "a",
            "expl": "Un assaillant retransmet une requête authentique (ex: un virement). L'utilisation de tokens à usage unique (nonce) ou d'un compteur de session neutralise le rejeu."
        },
        {
            "prompt": "Quel standard de sécurité des cartes de paiement exige des contrôles stricts sur le stockage et le traitement des numéros de cartes bancaires (PAN) ?",
            "opts": ["PCI-DSS (Payment Card Industry Data Security Standard)", "HIPAA", "RGPD uniquement", "SOX"],
            "corr": "a",
            "expl": "PCI-DSS définit les exigences obligatoires pour toute entité stockant, traitant ou transmettant des données de cartes bancaires."
        },
        {
            "prompt": "Dans la norme ISO 27001, quelle méthode est au cœur du Système de Management de la Sécurité de l'Information (SMSI) ?",
            "opts": [
                "L'analyse et l'évaluation continue des risques de sécurité de l'information",
                "L'achat obligatoire de pare-feux certifiés par le gouvernement",
                "L'interdiction absolue de tout accès Internet aux salariés",
                "L'archivage des données uniquement sur bandes magnétiques"
            ],
            "corr": "a",
            "expl": "ISO 27001 repose sur une approche par les risques pour concevoir, appliquer et améliorer continuellement les mesures de sécurité."
        },
        {
            "prompt": "Quelle commande d'inspection réseau en ligne de commande permet de capturer et d'analyser en temps réel les paquets circulant sur une interface réseau Linux ?",
            "opts": ["tcpdump", "netstat", "ip link", "traceroute"],
            "corr": "a",
            "expl": "tcpdump est le renifleur de paquets en ligne de commande de référence sous Linux, équivalent en console à Wireshark."
        },
        {
            "prompt": "Quel type de scan de ports Nmap envoie des paquets TCP avec le drapeau SYN sans terminer la poignée de main, limitant l'apparition dans les logs applicatifs ?",
            "opts": ["Scan SYN furtif (-sS)", "Scan TCP Connect (-sT)", "Scan UDP (-sU)", "Scan Ping simple (-sn)"],
            "corr": "a",
            "expl": "Le scan SYN furtif (-sS) n'établit jamais la connexion complète, ce qui évitait historiquement d'être consigné par les démons applicatifs."
        },
        {
            "prompt": "Dans le modèle OSI, à quel niveau opère un protocole de chiffrement comme IPsec ?",
            "opts": ["Couche 3 (Réseau)", "Couche 7 (Application)", "Couche 2 (Liaison)", "Couche 4 (Transport)"],
            "corr": "a",
            "expl": "IPsec opère au niveau de la couche réseau (IP), permettant de chiffrer l'ensemble du trafic de façon transparente pour les couches supérieures."
        },
        {
            "prompt": "Quel est l'objectif premier d'un exercice de cyber-crise de type 'Red Team vs Blue Team' ?",
            "opts": [
                "Éprouver la capacité réelle de détection et de réaction des équipes défensives face à un scénario d'attaque réaliste",
                "Remplacer les pare-feux et les antivirus de l'entreprise",
                "Calculer le coût total du matériel informatique",
                "Réécrire le code source de toutes les applications"
            ],
            "corr": "a",
            "expl": "La Red Team simule des assaillants réels, tandis que la Blue Team s'entraîne à détecter, endiguer et remédier à l'attaque en conditions réelles."
        },
        {
            "prompt": "Dans un chiffrement de type 'Masque Jetable' (Vernam / One-Time Pad), quelle condition mathématique est requise pour garantir le secret parfait absolu de Shannon ?",
            "opts": [
                "La clé doit être aussi longue que le message, totalement aléatoire, utilisée une seule fois et gardée secrète",
                "La clé doit être dérivée d'un grand nombre premier",
                "Le message doit être chiffré en bloc de 64 bits",
                "L'algorithme doit être exécuté sur un processeur quantique"
            ],
            "corr": "a",
            "expl": "Claude Shannon a démontré que le masque jetable offre une sécurité inconditionnelle théorique sous ces 4 strictes conditions."
        },
        {
            "prompt": "Quel vecteur d'attaque exploite la conversion et la désérialisation non sécurisée d'objets sérialisés (JSON, XML, Java/Python Pickling) ?",
            "opts": [
                "L'exécution de code arbitraire à distance (RCE) via désérialisation non sécurisée",
                "Une panne d'écran sur le poste client",
                "Un déni de service sur le protocole ARP",
                "Un mot de passe trop court dans Active Directory"
            ],
            "corr": "a",
            "expl": "La désérialisation de flux non fiables peut instancier des classes inattendues et exécuter du code malveillant côté serveur (ex: gadget chains)."
        },
        {
            "prompt": "Quelle mesure permet d'atténuer le risque lié aux attaques par force brute sur un formulaire de connexion web ?",
            "opts": [
                "L'instauration d'un rate limiting (limite de requêtes), d'un verrouillage temporaire de compte et d'un CAPTCHA",
                "La désactivation du protocole HTTPS",
                "L'affichage du mot de passe en clair dans l'URL",
                "L'autorisation des mots de passe vides"
            ],
            "corr": "a",
            "expl": "Limiter le nombre d'essais consécutifs et temporiser les réponses bloque les dictionnaires automatisés."
        },
        {
            "prompt": "Quelle est l'utilité du mécanisme de 'Honeypot' (pot de miel) en cybersécurité ?",
            "opts": [
                "Attirer les attaquants vers un système leurre pour étudier leurs méthodes sans compromettre la production",
                "Accélérer le débit des requêtes web légitimes",
                "Sauvegarder les bases de données SQL",
                "Chiffrer les clés privées SSH"
            ],
            "corr": "a",
            "expl": "Un honeypot est un leurre délibérément vulnérable ou exposé pour détecter précocement les scans et comportements hostiles."
        },
        {
            "prompt": "Quel type de chiffrement moderne permet de réaliser des calculs directement sur des données chiffrées sans jamais avoir à les déchiffrer au préalable ?",
            "opts": ["Le chiffrement homomorphe (FHE)", "Le chiffrement AES-CBC", "Le chiffrement RSA 4096", "Le chiffrement de Vigenère"],
            "corr": "a",
            "expl": "Le chiffrement homomorphe permet d'externaliser des calculs dans le cloud en préservant la confidentialité absolue des données manipulées."
        },
        {
            "prompt": "Quelle est la principale vulnérabilité introduite par la réutilisation d'un 'nonce' (Number used Once) dans le chiffrement AES-GCM ?",
            "opts": [
                "La perte totale de confidentialité et d'authenticité permettant de recouvrer la clé d'authentification GHASH",
                "Une augmentation de la latence réseau de 50%",
                "La corruption du système de fichiers hôte",
                "La désactivation automatique du pare-feu"
            ],
            "corr": "a",
            "expl": "Réutiliser le même nonce avec la même clé dans AES-GCM brise catastrophiquement la sécurité du cryptogramme et de l'intégrité."
        },
        {
            "prompt": "Quel est le rôle du protocole 'STARTTLS' dans les communications SMTP ou IMAP ?",
            "opts": [
                "Négocier à chaud une mise à niveau d'une connexion en texte clair vers une session chiffrée TLS",
                "Démarrer le système d'exploitation à distance",
                "Créer automatiquement un compte utilisateur sur le serveur",
                "Supprimer les pièces jointes volumineuses"
            ],
            "corr": "a",
            "expl": "STARTTLS indique au serveur de passer le canal existant en communication sécurisée chiffrée TLS."
        },
        {
            "prompt": "Dans la gestion des identités, que permet le mécanisme 'SSO' (Single Sign-On / Authentification unique) ?",
            "opts": [
                "Permettre à un utilisateur de s'authentifier une seule fois pour accéder à un ensemble d'applications différentes",
                "Imposer à chaque utilisateur de changer de mot de passe toutes les heures",
                "Interdire l'usage de smartphones en entreprise",
                "Désactiver l'accès à distance"
            ],
            "corr": "a",
            "expl": "Le SSO centralise l'authentification (via SAML, OIDC) pour simplifier l'accès utilisateur et renforcer la gouvernance des accès."
        },
        {
            "prompt": "Quel mécanisme garantit qu'un logiciel téléchargé n'a pas été corrompu ou altéré par un assaillant lors de son transit ?",
            "opts": [
                "La vérification de la signature numérique du paquet ou de son empreinte cryptographique (hash)",
                "L'enregistrement du fichier sur une clé USB neuve",
                "L'exécution en mode administrateur",
                "Le renommage de l'extension du fichier"
            ],
            "corr": "a",
            "expl": "La signature numérique du développeur validée avec sa clé publique garantit l'intégrité et l'authenticité binaire du binaire."
        },
        {
            "prompt": "Quelle est la fonction d'un 'WAF' (Web Application Firewall) comparé à un pare-feu de niveau réseau classique ?",
            "opts": [
                "Inspecter le trafic applicatif HTTP/HTTPS en profondeur pour bloquer les attaques comme les injections SQL et XSS",
                "Accélérer la vitesse de la fibre optique",
                "Bloquer uniquement les pings ICMP",
                "Gérer les baux d'adresses DHCP"
            ],
            "corr": "a",
            "expl": "Le WAF agit au niveau de la couche applicative (couche 7) pour filtrer les requêtes malveillantes dirigées contre les applications web."
        }
    ]

    for item in curated_cyber:
        opts_formatted = []
        for o_idx, opt_text in enumerate(item["opts"]):
            opts_formatted.append({"id": chr(97 + o_idx), "text": str(opt_text)})

        cyber_100.append({
            "ordering": len(cyber_100) + 1,
            "type": "single_choice",
            "prompt_markdown": item["prompt"],
            "points": 1.0,
            "negative_penalty": 0.5,
            "options_json": json.dumps(opts_formatted, ensure_ascii=False),
            "correct_answers_json": json.dumps(item["corr"], ensure_ascii=False),
            "explanation": item["expl"]
        })

    cyber_100 = cyber_100[:100]
    assert len(cyber_100) == 100, f"Expected 100 questions for CYBER_CRYPTO, got {len(cyber_100)}"

    # Save all 3 files
    out_py = os.path.join(seeds_dir, "seed_python_prog_100.json")
    out_sys = os.path.join(seeds_dir, "seed_sys_exploit_100.json")
    out_cyber = os.path.join(seeds_dir, "seed_cyber_crypto_100.json")

    with open(out_py, "w", encoding="utf-8") as f:
        json.dump(py_100, f, indent=2, ensure_ascii=False)
    print("Saved:", out_py, len(py_100), "questions")

    with open(out_sys, "w", encoding="utf-8") as f:
        json.dump(sys_100, f, indent=2, ensure_ascii=False)
    print("Saved:", out_sys, len(sys_100), "questions")

    with open(out_cyber, "w", encoding="utf-8") as f:
        json.dump(cyber_100, f, indent=2, ensure_ascii=False)
    print("Saved:", out_cyber, len(cyber_100), "questions")

if __name__ == "__main__":
    build_seeds()
