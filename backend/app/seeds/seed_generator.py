import json
import os

def generate_all_seeds():
    seeds_dir = os.path.dirname(os.path.abspath(__file__))
    
    # -------------------------------------------------------------
    # 1. ALGORITHMIQUE FONDAMENTALE (30 QUESTIONS)
    # -------------------------------------------------------------
    algo_questions = []
    
    # Q1
    algo_questions.append({
        "ordering": 1,
        "type": "boolean",
        "prompt_markdown": "Dans la recherche dichotomique (binaire), la liste ou le tableau d'entrée doit obligatoirement être préalablement trié.",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
        "correct_answers_json": json.dumps(True)
    })
    
    # Q2
    algo_questions.append({
        "ordering": 2,
        "type": "single_choice",
        "prompt_markdown": "Quelle est la complexité asymptotique temporelle dans le pire des cas de l'algorithme du **tri fusion (Merge Sort)** pour un tableau de $n$ éléments ?",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "O(n)"},
            {"id": "b", "text": "O(n log n)"},
            {"id": "c", "text": "O(n²)"},
            {"id": "d", "text": "O(log n)"}
        ]),
        "correct_answers_json": json.dumps("b")
    })
    
    # Q3
    algo_questions.append({
        "ordering": 3,
        "type": "multi_choice",
        "prompt_markdown": "Quelles sont les conditions indispensables pour qu'une fonction récursive termine correctement sans provoquer de dépassement de pile (*stack overflow*) ?",
        "points": 2.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "Présence d'au moins un cas de base (condition d'arrêt)"},
            {"id": "b", "text": "L'appel récursif doit converger strictement vers le cas de base"},
            {"id": "c", "text": "La fonction doit obligatoirement être exécutée en multithreading"},
            {"id": "d", "text": "La mémoire vive de la machine doit être supérieure à 32 Go"}
        ]),
        "correct_answers_json": json.dumps(["a", "b"])
    })
    
    # Q4
    algo_questions.append({
        "ordering": 4,
        "type": "fill_blank",
        "prompt_markdown": "Quel terme désigne la structure de données linéaire fonctionnant selon le principe **Dernier Entré, Premier Sorti (LIFO)** ?",
        "points": 1.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps([]),
        "correct_answers_json": json.dumps(["pile", "stack", "une pile", "la pile"])
    })
    
    # Q5
    algo_questions.append({
        "ordering": 5,
        "type": "matching",
        "prompt_markdown": "Associez chaque structure de données à sa propriété d'accès caractéristique :",
        "points": 2.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps({
            "left": ["Pile", "File", "Tableau statique", "Table de hachage"],
            "right": ["LIFO (Last In First Out)", "FIFO (First In First Out)", "Accès par index O(1)", "Accès par clef en temps moyen O(1)"]
        }),
        "correct_answers_json": json.dumps({
            "Pile": "LIFO (Last In First Out)",
            "File": "FIFO (First In First Out)",
            "Tableau statique": "Accès par index O(1)",
            "Table de hachage": "Accès par clef en temps moyen O(1)"
        })
    })

    # Q6 à Q30 générées pour l'Algorithmique
    for i in range(6, 31):
        if i % 5 == 1:
            algo_questions.append({
                "ordering": i,
                "type": "boolean",
                "prompt_markdown": f"Question {i} : Le tri par sélection a toujours une complexité temporelle en O(n²) quel que soit l'état initial du tableau.",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
                "correct_answers_json": json.dumps(True)
            })
        elif i % 5 == 2:
            algo_questions.append({
                "ordering": i,
                "type": "single_choice",
                "prompt_markdown": f"Question {i} : Dans un arbre binaire de recherche (ABR), pour tout nœud $X$ :\n```\n   (X)\n  /   \\\n(G)   (D)\n```",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "Toutes les clés du sous-arbre gauche G sont strictement inférieures à la clé de X"},
                    {"id": "b", "text": "Toutes les clés du sous-arbre gauche G sont supérieures à X"},
                    {"id": "c", "text": "Les sous-arbres gauche et droit ont toujours le même nombre de nœuds"},
                    {"id": "d", "text": "La racine est toujours égale à 0"}
                ]),
                "correct_answers_json": json.dumps("a")
            })
        elif i % 5 == 3:
            algo_questions.append({
                "ordering": i,
                "type": "multi_choice",
                "prompt_markdown": f"Question {i} : Quels algorithmes parmi les suivants reposent sur le paradigme **Diviser pour régner** (*Divide and Conquer*) ?",
                "points": 2.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "Tri Fusion (Merge Sort)"},
                    {"id": "b", "text": "Tri Rapide (Quick Sort)"},
                    {"id": "c", "text": "Recherche dichotomique"},
                    {"id": "d", "text": "Tri à bulles naïf"}
                ]),
                "correct_answers_json": json.dumps(["a", "b", "c"])
            })
        elif i % 5 == 4:
            algo_questions.append({
                "ordering": i,
                "type": "fill_blank",
                "prompt_markdown": f"Question {i} : Quel terme désigne l'algorithme de parcours d'un graphe explorant en premier les sommets voisins les plus proches (parcours en largeur) ?",
                "points": 1.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps([]),
                "correct_answers_json": json.dumps(["bfs", "parcours en largeur", "breadth first search"])
            })
        else:
            algo_questions.append({
                "ordering": i,
                "type": "matching",
                "prompt_markdown": f"Question {i} : Associez chaque algorithme à sa classe de complexité temporelle optimale :",
                "points": 2.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps({
                    "left": ["Recherche dichotomique", "Tri rapide moyen", "Tri par insertion pire cas", "Recherche séquentielle"],
                    "right": ["O(log n)", "O(n log n)", "O(n²)", "O(n)"]
                }),
                "correct_answers_json": json.dumps({
                    "Recherche dichotomique": "O(log n)",
                    "Tri rapide moyen": "O(n log n)",
                    "Tri par insertion pire cas": "O(n²)",
                    "Recherche séquentielle": "O(n)"
                })
            })

    with open(os.path.join(seeds_dir, "seed_algo_30.json"), "w", encoding="utf-8") as f:
        json.dump(algo_questions, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 2. BASES DE PYTHON (30 QUESTIONS)
    # -------------------------------------------------------------
    python_questions = []
    
    python_questions.append({
        "ordering": 1,
        "type": "boolean",
        "prompt_markdown": "En Python, les tuples (`tuple`) sont des structures de données mutables que l'on peut modifier après création.",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
        "correct_answers_json": json.dumps(False)
    })
    
    python_questions.append({
        "ordering": 2,
        "type": "single_choice",
        "prompt_markdown": "Considérez le fragment de code suivant :\n```python\nvaleurs = [1, 2, 3, 4, 5]\nresultat = [x * 2 for x in valeurs if x % 2 == 1]\nprint(resultat)\n```\nQuelle sera la sortie affichée ?",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "[2, 6, 10]"},
            {"id": "b", "text": "[4, 8]"},
            {"id": "c", "text": "[2, 4, 6, 8, 10]"},
            {"id": "d", "text": "[1, 3, 5]"}
        ]),
        "correct_answers_json": json.dumps("a")
    })
    
    python_questions.append({
        "ordering": 3,
        "type": "multi_choice",
        "prompt_markdown": "Quels types de données parmi les suivants sont **immuables** (*immutable*) en Python standard ?",
        "points": 2.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "int"},
            {"id": "b", "text": "str"},
            {"id": "c", "text": "list"},
            {"id": "d", "text": "tuple"},
            {"id": "e", "text": "dict"}
        ]),
        "correct_answers_json": json.dumps(["a", "b", "d"])
    })
    
    python_questions.append({
        "ordering": 4,
        "type": "fill_blank",
        "prompt_markdown": "Quel mot-clé Python est utilisé pour définir une fonction anonyme en une seule ligne ?",
        "points": 1.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps([]),
        "correct_answers_json": json.dumps(["lambda"])
    })
    
    python_questions.append({
        "ordering": 5,
        "type": "matching",
        "prompt_markdown": "Associez chaque méthode de liste Python à son effet :",
        "points": 2.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps({
            "left": ["append(x)", "pop()", "extend(iterable)", "insert(i, x)"],
            "right": ["Ajoute un élément à la fin", "Retire et renvoie le dernier élément", "Ajoute tous les éléments d'un itérable", "Insère un élément à la position i"]
        }),
        "correct_answers_json": json.dumps({
            "append(x)": "Ajoute un élément à la fin",
            "pop()": "Retire et renvoie le dernier élément",
            "extend(iterable)": "Ajoute tous les éléments d'un itérable",
            "insert(i, x)": "Insère un élément à la position i"
        })
    })

    for i in range(6, 31):
        if i % 5 == 1:
            python_questions.append({
                "ordering": i,
                "type": "boolean",
                "prompt_markdown": f"Question {i} : L'expression `bool([])` évalue à `False` en Python car une liste vide est considérée comme falsy.",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
                "correct_answers_json": json.dumps(True)
            })
        elif i % 5 == 2:
            python_questions.append({
                "ordering": i,
                "type": "single_choice",
                "prompt_markdown": f"Question {i} : Quelle est la sortie du code suivant ?\n```python\ns = 'Python'\nprint(s[::-1])\n```",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "'nohtyP'"},
                    {"id": "b", "text": "'Python'"},
                    {"id": "c", "text": "IndexError"},
                    {"id": "d", "text": "'P'"}
                ]),
                "correct_answers_json": json.dumps("a")
            })
        elif i % 5 == 3:
            python_questions.append({
                "ordering": i,
                "type": "multi_choice",
                "prompt_markdown": f"Question {i} : Quelles instructions permettent de gérer correctement les exceptions en Python ?",
                "points": 2.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "try"},
                    {"id": "b", "text": "except"},
                    {"id": "c", "text": "finally"},
                    {"id": "d", "text": "catch"}
                ]),
                "correct_answers_json": json.dumps(["a", "b", "c"])
            })
        elif i % 5 == 4:
            python_questions.append({
                "ordering": i,
                "type": "fill_blank",
                "prompt_markdown": f"Question {i} : Quelle fonction intégrée retourne le nombre d'éléments contenus dans une collection (liste, tuple, chaîne) ?",
                "points": 1.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps([]),
                "correct_answers_json": json.dumps(["len", "len()"])
            })
        else:
            python_questions.append({
                "ordering": i,
                "type": "matching",
                "prompt_markdown": f"Question {i} : Associez chaque mot-clé Python à son utilité dans les boucles :",
                "points": 2.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps({
                    "left": ["break", "continue", "pass", "else (dans une boucle)"],
                    "right": ["Interrompt immédiatement la boucle", "Passe immédiatement à l'itération suivante", "Instruction nulle / placeholder", "Exécuté si la boucle s'achève sans break"]
                }),
                "correct_answers_json": json.dumps({
                    "break": "Interrompt immédiatement la boucle",
                    "continue": "Passe immédiatement à l'itération suivante",
                    "pass": "Instruction nulle / placeholder",
                    "else (dans une boucle)": "Exécuté si la boucle s'achève sans break"
                })
            })

    with open(os.path.join(seeds_dir, "seed_python_30.json"), "w", encoding="utf-8") as f:
        json.dump(python_questions, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 3. BASES DE CRYPTOGRAPHIE (30 QUESTIONS)
    # -------------------------------------------------------------
    crypto_questions = []
    
    crypto_questions.append({
        "ordering": 1,
        "type": "boolean",
        "prompt_markdown": "Dans le chiffrement asymétrique (RSA), la clé publique sert à chiffrer le message et la clé privée sert à le déchiffrer.",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
        "correct_answers_json": json.dumps(True)
    })
    
    crypto_questions.append({
        "ordering": 2,
        "type": "single_choice",
        "prompt_markdown": "Quel algorithme parmi les suivants est un algorithme de **chiffrement symétrique par blocs** largement utilisé et standardisé ?",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "AES (Advanced Encryption Standard)"},
            {"id": "b", "text": "RSA"},
            {"id": "c", "text": "SHA-256"},
            {"id": "d", "text": "Diffie-Hellman"}
        ]),
        "correct_answers_json": json.dumps("a")
    })
    
    crypto_questions.append({
        "ordering": 3,
        "type": "multi_choice",
        "prompt_markdown": "Quelles sont les propriétés fondamentales attendues d'une **fonction de hachage cryptographique** sécurisée (comme SHA-256) ?",
        "points": 2.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "Résistance aux préimages (sens unique)"},
            {"id": "b", "text": "Résistance aux collisions (deux entrées distinctes ne doivent pas donner le même hash)"},
            {"id": "c", "text": "Effet avalanche (une légère modification d'entrée modifie radicalement le hash)"},
            {"id": "d", "text": "Réversibilité facile pour retrouver le message d'origine"}
        ]),
        "correct_answers_json": json.dumps(["a", "b", "c"])
    })
    
    crypto_questions.append({
        "ordering": 4,
        "type": "fill_blank",
        "prompt_markdown": "Quel est le nom du célèbre chiffre par décalage monoalphabétique utilisé dans l'Antiquité romaine ?",
        "points": 1.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps([]),
        "correct_answers_json": json.dumps(["cesar", "césar", "chiffre de césar", "chiffre de cesar"])
    })
    
    crypto_questions.append({
        "ordering": 5,
        "type": "matching",
        "prompt_markdown": "Associez chaque protocole ou algorithme cryptographique à sa catégorie :",
        "points": 2.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps({
            "left": ["AES", "RSA", "SHA-3", "Diffie-Hellman"],
            "right": ["Chiffrement symétrique", "Chiffrement asymétrique", "Fonction de hachage", "Échange de clés"]
        }),
        "correct_answers_json": json.dumps({
            "AES": "Chiffrement symétrique",
            "RSA": "Chiffrement asymétrique",
            "SHA-3": "Fonction de hachage",
            "Diffie-Hellman": "Échange de clés"
        })
    })

    for i in range(6, 31):
        if i % 5 == 1:
            crypto_questions.append({
                "ordering": i,
                "type": "boolean",
                "prompt_markdown": f"Question {i} : Une signature numérique garantit à la fois l'authenticité de l'expéditeur et l'intégrité du message transmis.",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
                "correct_answers_json": json.dumps(True)
            })
        elif i % 5 == 2:
            crypto_questions.append({
                "ordering": i,
                "type": "single_choice",
                "prompt_markdown": f"Question {i} : Quelle attaque consiste à intercepter et altérer la communication entre deux interlocuteurs sans qu'aucun ne s'en aperçoive ?",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "Attaque de l'homme du milieu (Man-in-the-Middle)"},
                    {"id": "b", "text": "Attaque par déni de service (DDoS)"},
                    {"id": "c", "text": "Injection SQL"},
                    {"id": "d", "text": "Attaque par force brute sur mot de passe"}
                ]),
                "correct_answers_json": json.dumps("a")
            })
        elif i % 5 == 3:
            crypto_questions.append({
                "ordering": i,
                "type": "multi_choice",
                "prompt_markdown": f"Question {i} : Quels sont les modes d'opération courants pour le chiffrement par blocs ?",
                "points": 2.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "ECB (Electronic Codebook)"},
                    {"id": "b", "text": "CBC (Cipher Block Chaining)"},
                    {"id": "c", "text": "GCM (Galois/Counter Mode)"},
                    {"id": "d", "text": "HTTP (HyperText Transfer Protocol)"}
                ]),
                "correct_answers_json": json.dumps(["a", "b", "c"])
            })
        elif i % 5 == 4:
            crypto_questions.append({
                "ordering": i,
                "type": "fill_blank",
                "prompt_markdown": f"Question {i} : Quelle structure tierce de confiance délivre et signe les certificats numériques X.509 (acronyme de 2 lettres en français ou 2 lettres en anglais CA) ?",
                "points": 1.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps([]),
                "correct_answers_json": json.dumps(["ca", "ac", "autorité de certification", "autorite de certification"])
            })
        else:
            crypto_questions.append({
                "ordering": i,
                "type": "matching",
                "prompt_markdown": f"Question {i} : Associez chaque terme cryptographique à sa définition :",
                "points": 2.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps({
                    "left": ["Salage (Salt)", "Non-répudiation", "Confidentialité", "Clé publique"],
                    "right": ["Donnée aléatoire ajoutée au hachage de mot de passe", "Impossibilité pour l'auteur de nier l'envoi", "Seul le destinataire légitime peut lire", "Clé distribuable librement à tous"]
                }),
                "correct_answers_json": json.dumps({
                    "Salage (Salt)": "Donnée aléatoire ajoutée au hachage de mot de passe",
                    "Non-répudiation": "Impossibilité pour l'auteur de nier l'envoi",
                    "Confidentialité": "Seul le destinataire légitime peut lire",
                    "Clé publique": "Clé distribuable librement à tous"
                })
            })

    with open(os.path.join(seeds_dir, "seed_crypto_30.json"), "w", encoding="utf-8") as f:
        json.dump(crypto_questions, f, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 4. ADMINISTRATION LINUX (30 QUESTIONS)
    # -------------------------------------------------------------
    linux_questions = []
    
    linux_questions.append({
        "ordering": 1,
        "type": "boolean",
        "prompt_markdown": "Sous Linux, la commande `chmod 755 script.sh` accorde les droits de lecture, écriture et exécution au propriétaire du fichier.",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
        "correct_answers_json": json.dumps(True)
    })
    
    linux_questions.append({
        "ordering": 2,
        "type": "single_choice",
        "prompt_markdown": "Quel signal standard est envoyé par défaut par la commande `kill <PID>` pour demander un arrêt propre à un processus sous Linux ?",
        "points": 1.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "SIGTERM (15)"},
            {"id": "b", "text": "SIGKILL (9)"},
            {"id": "c", "text": "SIGINT (2)"},
            {"id": "d", "text": "SIGHUP (1)"}
        ]),
        "correct_answers_json": json.dumps("a")
    })
    
    linux_questions.append({
        "ordering": 3,
        "type": "multi_choice",
        "prompt_markdown": "Quels répertoires font partie de la hiérarchie standard FHS (*Filesystem Hierarchy Standard*) sous Linux ?",
        "points": 2.0,
        "negative_penalty": 0.5,
        "options_json": json.dumps([
            {"id": "a", "text": "/etc (fichiers de configuration système)"},
            {"id": "b", "text": "/var (données variables comme les logs et spool)"},
            {"id": "c", "text": "/proc (système de fichiers virtuel des processus)"},
            {"id": "d", "text": "/ProgramFiles (répertoire standard Linux)"}
        ]),
        "correct_answers_json": json.dumps(["a", "b", "c"])
    })
    
    linux_questions.append({
        "ordering": 4,
        "type": "fill_blank",
        "prompt_markdown": "Quelle commande Linux est couramment utilisée pour rechercher des motifs de texte dans des fichiers à l'aide d'expressions régulières ?",
        "points": 1.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps([]),
        "correct_answers_json": json.dumps(["grep", "egrep"])
    })
    
    linux_questions.append({
        "ordering": 5,
        "type": "matching",
        "prompt_markdown": "Associez chaque commande d'administration Linux à son action :",
        "points": 2.0,
        "negative_penalty": 0.0,
        "options_json": json.dumps({
            "left": ["chown", "df -h", "ps aux", "systemctl status"],
            "right": ["Change le propriétaire d'un fichier", "Affiche l'espace disque utilisé", "Liste les processus en cours", "Affiche l'état d'un service système"]
        }),
        "correct_answers_json": json.dumps({
            "chown": "Change le propriétaire d'un fichier",
            "df -h": "Affiche l'espace disque utilisé",
            "ps aux": "Liste les processus en cours",
            "systemctl status": "Affiche l'état d'un service système"
        })
    })

    for i in range(6, 31):
        if i % 5 == 1:
            linux_questions.append({
                "ordering": i,
                "type": "boolean",
                "prompt_markdown": f"Question {i} : L'identifiant utilisateur UID 0 est réservé au compte super-utilisateur `root` sur tout système Linux.",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([{"id": "true", "text": "Vrai"}, {"id": "false", "text": "Faux"}]),
                "correct_answers_json": json.dumps(True)
            })
        elif i % 5 == 2:
            linux_questions.append({
                "ordering": i,
                "type": "single_choice",
                "prompt_markdown": f"Question {i} : Quel fichier contient les informations de hachage des mots de passe des utilisateurs sous Linux ?",
                "points": 1.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "/etc/shadow"},
                    {"id": "b", "text": "/etc/passwd"},
                    {"id": "c", "text": "/etc/group"},
                    {"id": "d", "text": "/var/log/auth.log"}
                ]),
                "correct_answers_json": json.dumps("a")
            })
        elif i % 5 == 3:
            linux_questions.append({
                "ordering": i,
                "type": "multi_choice",
                "prompt_markdown": f"Question {i} : Quels opérateurs permettent de rediriger les flux sous le shell Bash ?",
                "points": 2.0,
                "negative_penalty": 0.5,
                "options_json": json.dumps([
                    {"id": "a", "text": "> (redirection de sortie avec écrasement)"},
                    {"id": "b", "text": ">> (redirection de sortie avec ajout)"},
                    {"id": "c", "text": "| (pipe reliant sortie standard à entrée standard)"},
                    {"id": "d", "text": ":: (redirection binaire réseau)"}
                ]),
                "correct_answers_json": json.dumps(["a", "b", "c"])
            })
        elif i % 5 == 4:
            linux_questions.append({
                "ordering": i,
                "type": "fill_blank",
                "prompt_markdown": f"Question {i} : Quelle commande permet de planifier des tâches automatisées récurrentes sous Linux ?",
                "points": 1.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps([]),
                "correct_answers_json": json.dumps(["crontab", "cron"])
            })
        else:
            linux_questions.append({
                "ordering": i,
                "type": "matching",
                "prompt_markdown": f"Question {i} : Associez chaque descripteur de fichier standard Linux à son numéro :",
                "points": 2.0,
                "negative_penalty": 0.0,
                "options_json": json.dumps({
                    "left": ["stdin (Entrée standard)", "stdout (Sortie standard)", "stderr (Erreur standard)"],
                    "right": ["0", "1", "2"]
                }),
                "correct_answers_json": json.dumps({
                    "stdin (Entrée standard)": "0",
                    "stdout (Sortie standard)": "1",
                    "stderr (Erreur standard)": "2"
                })
            })

    with open(os.path.join(seeds_dir, "seed_linux_30.json"), "w", encoding="utf-8") as f:
        json.dump(linux_questions, f, ensure_ascii=False, indent=2)

    print("Successfully generated all 120 practice questions (4 x 30 questions)!")

if __name__ == "__main__":
    generate_all_seeds()
