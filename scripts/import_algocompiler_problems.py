import json
import os
import glob

def run():
    probs_dir = os.path.join("oldapps", "AlgoCompilerv2", "AlgoCompilerv2", "AlgoCompiler", "src", "web", "data", "problems")
    files = glob.glob(os.path.join(probs_dir, "*.json"))
    print(f"Found problem files: {len(files)}")

    imported = []
    for fpath in sorted(files):
        if "manifest" in fpath:
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                p = json.load(f)
            
            tc = p.get("test_cases", [])
            pub = [{"input": t.get("input", ""), "output": str(t.get("expected_output", "")).strip()} for t in tc if t.get("is_public")]
            hid = [{"input": t.get("input", ""), "output": str(t.get("expected_output", "")).strip()} for t in tc if not t.get("is_public")]
            
            while len(pub) < 2 and len(hid) > 1:
                pub.append(hid.pop(0))
                
            if len(pub) < 2 and len(pub) >= 1:
                sample = pub[0]
                pub.append({"input": sample["input"], "output": sample["output"]})
                
            base_id = os.path.basename(fpath).split("-")[0]
            try:
                pid = 9000 + int(base_id)
            except Exception:
                pid = 9000 + len(imported) + 1
                
            # Preserve customized starter_code if already defined in existing coding_challenges.json
            existing_starters = {}
            if os.path.exists(os.path.join("backend", "app", "data", "python_training", "coding_challenges.json")):
                try:
                    with open(os.path.join("backend", "app", "data", "python_training", "coding_challenges.json"), "r", encoding="utf-8") as cur_f:
                        for item in json.load(cur_f):
                            if item.get("id") and item.get("starter_code"):
                                existing_starters[item["id"]] = item["starter_code"]
                except Exception:
                    pass

            starter_code = existing_starters.get(pid, (
                "# Solution en Python standard (stdin / stdout)\n"
                "import sys\n\n"
                "def solve():\n"
                "    tokens = sys.stdin.read().split()\n"
                "    if not tokens:\n"
                "        return\n"
                "    # TODO: Écrivez votre logique algorithmique ici\n\n"
                "if __name__ == '__main__':\n"
                "    solve()\n"
            ))
            
            diff = p.get("difficulty", "Medium").lower()
            pts = 4.0 if diff == "hard" else (3.0 if diff == "medium" else 2.0)
            
            imported.append({
                "id": pid,
                "is_exam": False,
                "type": "coding",
                "title": p.get("title", "Problème Algorithmique"),
                "topic": p.get("topic", "Algorithms"),
                "difficulty": diff,
                "description": p.get("description", ""),
                "starter_code": starter_code,
                "public_tests": pub,
                "hidden_tests": hid,
                "points": pts,
                "hint1": "Pensez aux cas limites (valeurs nulles, négatives, extrêmes).",
                "hint2": "Vérifiez que la complexité temporelle est optimale pour éviter les dépassements de délai."
            })
        except Exception as e:
            print(f"Error reading {fpath}: {e}")

    print(f"Successfully processed {len(imported)} AlgoCompiler problems.")
    
    out_dir = os.path.join("backend", "app", "data", "python_training")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "coding_challenges.json")
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(imported, out_f, indent=2, ensure_ascii=False)
    print(f"Saved coding challenges to {out_path}")
    
    # Also add an 11th chapter or enrich existing chapters in curriculum.json
    curr_path = os.path.join(out_dir, "curriculum.json")
    if os.path.exists(curr_path):
        with open(curr_path, "r", encoding="utf-8") as f:
            curr = json.load(f)
            
        # Check if AlgoCompiler chapter exists
        ch_algo = None
        for ch in curr["chapters"]:
            if ch["id"] == "algocompiler_challenges":
                ch_algo = ch
                break
                
        if not ch_algo:
            ch_algo = {
                "id": "algocompiler_challenges",
                "title": "Défis Algorithmiques Avancés (AlgoCompiler / HackerRank)",
                "order": 11,
                "description": "47 défis classiques d'algorithmique et structures de données (matrices, listes, piles, maths) avec tests publics et tests cachés.",
                "coding_exercises_count": len(imported),
                "mcq_questions_count": 0,
                "coding_exercises": imported,
                "mcq_questions": []
            }
            curr["chapters"].append(ch_algo)
        else:
            ch_algo["coding_exercises"] = imported
            ch_algo["coding_exercises_count"] = len(imported)
            
        with open(curr_path, "w", encoding="utf-8") as f:
            json.dump(curr, f, indent=2, ensure_ascii=False)
        print("Updated curriculum.json with AlgoCompiler challenges.")

if __name__ == "__main__":
    run()

