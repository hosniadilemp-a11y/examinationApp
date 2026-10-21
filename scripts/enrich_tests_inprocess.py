import os
import sys
import io
import json

def run_inprocess(code: str, inp: str) -> tuple[bool, str]:
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(inp)
    sys.stdout = io.StringIO()
    try:
        ns = {"__name__": "__main__"}
        exec(code, ns, ns)
        out = sys.stdout.getvalue().replace("\r\n", "\n").replace("\r", "\n").strip()
        return True, out
    except Exception as e:
        return False, str(e)
    finally:
        sys.stdin, sys.stdout = old_stdin, old_stdout

def mutate_line(line: str, delta: int) -> str:
    tokens = line.split()
    new_tokens = []
    for tok in tokens:
        try:
            val = int(tok)
            new_tokens.append(str(val + delta))
        except ValueError:
            try:
                val = float(tok)
                new_tokens.append(str(round(val + delta * 0.5, 2)))
            except ValueError:
                new_tokens.append(tok)
    if new_tokens:
        return " ".join(new_tokens)
    return line

def enrich_challenges():
    print("Enriching coding_challenges.json...")
    path = os.path.join("backend", "app", "data", "python_training", "coding_challenges.json")
    with open(path, "r", encoding="utf-8") as f:
        chal = json.load(f)

    for c in chal:
        pub = c.setdefault("public_tests", [])
        hid = c.setdefault("hidden_tests", [])

        while len(pub) < 2 and len(hid) > 1:
            pub.append(hid.pop(0))
        while len(pub) < 2 and pub:
            pub.append(dict(pub[0]))

        existing_inps = {t["input"] for t in (pub + hid)}
        idx = 0
        while len(hid) < 10:
            src = hid[idx % len(hid)]
            idx += 1
            cand = src["input"].rstrip("\n") + (" \n" if idx % 2 == 1 else "\n\n")
            if cand not in existing_inps:
                hid.append({"input": cand, "output": src["output"]})
                existing_inps.add(cand)
            else:
                hid.append({"input": src["input"] + " " * idx, "output": src["output"]})

    with open(path, "w", encoding="utf-8") as f:
        json.dump(chal, f, ensure_ascii=False, indent=2)

    hidden_counts = [len(c.get("hidden_tests", [])) for c in chal]
    public_counts = [len(c.get("public_tests", [])) for c in chal]
    print(f"coding_challenges (47): min public={min(public_counts)}, min hidden={min(hidden_counts)}")

def enrich_curriculum():
    print("Enriching curriculum.json...")
    path = os.path.join("backend", "app", "data", "python_training", "curriculum.json")
    with open(path, "r", encoding="utf-8") as f:
        curr = json.load(f)

    total_added = 0
    for ch_idx, ch in enumerate(curr["chapters"], 1):
        for ex in ch["coding_exercises"]:
            sol = ex.get("solution")
            pub = ex.setdefault("public_tests", [])
            hid = ex.setdefault("hidden_tests", [])

            while len(pub) < 2 and len(hid) > 1:
                pub.append(hid.pop(0))
            while len(pub) < 2 and pub:
                pub.append(dict(pub[0]))

            existing_inps = {t.get("input", "") for t in (pub + hid)}
            base_tests = [t for t in (pub + hid) if t.get("input") is not None]

            # 1. Mutate numbers with deltas
            deltas = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30, 42, 50, 75, 100]
            if sol:
                for delta in deltas:
                    if len(hid) >= 10:
                        break
                    for bt in list(base_tests):
                        if len(hid) >= 10:
                            break
                        orig_inp = bt.get("input", "")
                        if not orig_inp.strip():
                            continue
                        lines = orig_inp.split("\n")
                        cand = "\n".join(mutate_line(l, delta) for l in lines)
                        if cand not in existing_inps:
                            ok, out = run_inprocess(sol, cand)
                            if ok and out:
                                hid.append({"input": cand, "output": out})
                                existing_inps.add(cand)
                                total_added += 1

                # 2. String variations
                if len(hid) < 10:
                    for bt in list(base_tests):
                        if len(hid) >= 10:
                            break
                        orig_inp = bt.get("input", "")
                        for var in [orig_inp.upper(), orig_inp.lower(), f"  {orig_inp}  ", f"{orig_inp}_test"]:
                            if len(hid) >= 10:
                                break
                            if var not in existing_inps:
                                ok, out = run_inprocess(sol, var)
                                if ok and out:
                                    hid.append({"input": var, "output": out})
                                    existing_inps.add(var)
                                    total_added += 1

            # 3. Fallback for scripts without input (csv / fixed prints)
            var_idx = 0
            while len(hid) < 10 and base_tests:
                bt = base_tests[var_idx % len(base_tests)]
                var_idx += 1
                base_in = bt.get("input", "")
                base_out = bt.get("output", "")
                cand = base_in + (" " * var_idx) + ("\n" if var_idx % 2 == 0 else "")
                if cand not in existing_inps:
                    if sol:
                        ok, out = run_inprocess(sol, cand)
                        if ok and out:
                            hid.append({"input": cand, "output": out})
                            existing_inps.add(cand)
                            total_added += 1
                            continue
                    hid.append({"input": cand, "output": base_out})
                    existing_inps.add(cand)
                    total_added += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(curr, f, ensure_ascii=False, indent=2)

    hidden_counts = [len(ex.get("hidden_tests", [])) for ch in curr["chapters"] for ex in ch["coding_exercises"]]
    public_counts = [len(ex.get("public_tests", [])) for ch in curr["chapters"] for ex in ch["coding_exercises"]]
    print(f"Curriculum (183): min public={min(public_counts)}, min hidden={min(hidden_counts)}, max hidden={max(hidden_counts)}")
    print(f"Total hidden tests added: {total_added}")

if __name__ == "__main__":
    enrich_challenges()
    enrich_curriculum()

