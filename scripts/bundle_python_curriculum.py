import os
import json
import importlib.util

def load_module_from_file(filepath):
    spec = importlib.util.spec_from_file_location("dynamic_mod", filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def bundle_curriculum():
    base_src = os.path.join("oldapps", "QuizApp", "QuizApp", "src", "data")
    coding_dir = os.path.join(base_src, "coding_questions")
    mcq_dir = os.path.join(base_src, "questions")
    
    output_dir = os.path.join("backend", "app", "data", "python_training")
    os.makedirs(output_dir, exist_ok=True)
    
    chapters_metadata = [
        {"id": "python_basics", "title": "Bases de Python & Syntaxe", "order": 1, "description": "Variables, types primitifs, entrées/sorties et opérations fondamentales"},
        {"id": "python_data_types", "title": "Structures de Données", "order": 2, "description": "Listes, tuples, ensembles (sets) et dictionnaires"},
        {"id": "control_flow", "title": "Structures de Contrôle", "order": 3, "description": "Conditions if/elif/else, boucles for et while"},
        {"id": "modules_de_base", "title": "Modules & Fonctions Intégrées", "order": 4, "description": "Modules standard math, random, sys, datetime et fonctions built-in"},
        {"id": "list_comprehension", "title": "Compréhensions de Listes & Générateurs", "order": 5, "description": "Syntaxes concises de listes, dictionnaires et générateurs"},
        {"id": "i_o", "title": "Entrées / Sorties & Fichiers", "order": 6, "description": "Manipulation de fichiers texte, CSV, context managers with"},
        {"id": "oop", "title": "Programmation Orientée Objet (POO)", "order": 7, "description": "Classes, objets, méthodes, héritage, encapsulation et polymorphisme"},
        {"id": "numpy", "title": "Calcul Scientifique avec NumPy", "order": 8, "description": "Tableaux ndarray, vectorisation, slicing, broadcasting et algèbre"},
        {"id": "pandas", "title": "Analyse de Données avec Pandas", "order": 9, "description": "DataFrames, Series, filtrage, agrégations et jointures"},
        {"id": "data_visualization", "title": "Visualisation de Données", "order": 10, "description": "Graphiques avec Matplotlib et Seaborn"}
    ]
    
    curriculum = {
        "chapters": [],
        "total_mcqs": 0,
        "total_coding": 0
    }
    
    for ch in chapters_metadata:
        ch_id = ch["id"]
        coding_file = os.path.join(coding_dir, f"{ch_id}.py")
        mcq_file = os.path.join(mcq_dir, f"{ch_id}.py")
        
        coding_list = []
        if os.path.exists(coding_file):
            mod_c = load_module_from_file(coding_file)
            coding_list = getattr(mod_c, "QUESTIONS", [])
            
        mcq_list = []
        if os.path.exists(mcq_file):
            mod_m = load_module_from_file(mcq_file)
            mcq_list = getattr(mod_m, "QUESTIONS", [])
            
        ch_data = {
            "id": ch_id,
            "title": ch["title"],
            "order": ch["order"],
            "description": ch["description"],
            "coding_exercises_count": len(coding_list),
            "mcq_questions_count": len(mcq_list),
            "coding_exercises": coding_list,
            "mcq_questions": mcq_list
        }
        
        curriculum["chapters"].append(ch_data)
        curriculum["total_coding"] += len(coding_list)
        curriculum["total_mcqs"] += len(mcq_list)
        print(f"Chapitre '{ch['title']}': {len(mcq_list)} QCM, {len(coding_list)} exercices de code.")
        
    out_file = os.path.join(output_dir, "curriculum.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(curriculum, f, ensure_ascii=False, indent=2)
        
    print(f"\nBundle complet sauvegardé dans {out_file} !")
    print(f"Total: {curriculum['total_mcqs']} QCM et {curriculum['total_coding']} exercices de code.")

if __name__ == "__main__":
    bundle_curriculum()
