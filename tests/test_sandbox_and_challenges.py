import pytest
from backend.app.services.sandbox_runner import (
    execute_user_code_with_input,
    execute_user_code_against_tests,
    normalize_output
)

def test_sandbox_stdin_stdout_execution():
    code = "import sys\nval = sys.stdin.read().strip()\nprint(f'Echo: {val}')"
    res = execute_user_code_with_input(code, "Adel", timeout_seconds=3.0)
    assert res["success"] is True
    assert res["stdout"].strip() == "Echo: Adel"
    assert res["timed_out"] is False

def test_sandbox_public_and_hidden_tests_masking():
    code = (
        "import sys\n"
        "lines = sys.stdin.read().strip().split()\n"
        "if lines:\n"
        "    a, b = int(lines[0]), int(lines[1])\n"
        "    print(a + b)\n"
    )
    test_cases = [
        {"id": "tc1", "input": "5 7\n", "output": "12", "is_public": True},
        {"id": "tc2", "input": "-3 10\n", "output": "7", "is_public": True},
        {"id": "tc3", "input": "100 200\n", "output": "300", "is_public": False}
    ]
    
    res = execute_user_code_against_tests(code, test_cases, timeout_seconds=3.0, mask_hidden_output=True)
    assert res["all_passed"] is True
    assert res["passed_count"] == 3
    assert res["total_count"] == 3
    
    # Public tests reveal input and expected output
    assert res["results"][0]["input"] == "5 7\n"
    assert res["results"][0]["expected_output"] == "12"
    assert res["results"][0]["is_public"] is True
    
    # Hidden tests MASK input and expected output to guarantee secret
    assert res["results"][2]["is_public"] is False
    assert res["results"][2]["input"] == "[Test Caché]"
    assert res["results"][2]["expected_output"] == "[Protégé]"

def test_sandbox_timeout_handling():
    infinite_loop = "while True:\n    pass\n"
    test_cases = [{"id": "tc1", "input": "", "output": "ok", "is_public": True}]
    res = execute_user_code_against_tests(infinite_loop, test_cases, timeout_seconds=0.8)
    assert res["all_passed"] is False
    assert "Délai" in res["results"][0]["error"] or "dépassé" in res["results"][0]["error"]

def test_api_run_code_and_run_tests_endpoints(client, student_headers):
    # 1. Tester run-code avec stdin
    r1 = client.post("/api/training/python/run-code", json={
        "code": "name = input()\nprint(f'Bienvenue {name} !')",
        "stdin": "Antigravity",
        "timeout": 3.0
    }, headers=student_headers)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["success"] is True
    assert "Bienvenue Antigravity !" in d1["stdout"]

    # 2. Tester run-tests sur exercice 1003 (public tests only)
    r2 = client.post("/api/training/python/run-tests", json={
        "exercise_id": 1003,
        "code": "u = input().strip().lower().replace(' ', '_')\nprint(u)",
        "run_all": False
    }, headers=student_headers)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["all_passed"] is True
    assert d2["total_count"] >= 2
    # Public test revealed
    assert d2["results"][0]["is_public"] is True
    assert d2["results"][0]["expected_output"] != "[Protégé]"

    # 3. Tester run-tests avec run_all=True (submission)
    r3 = client.post("/api/training/python/run-tests", json={
        "exercise_id": 1003,
        "code": "u = input().strip().lower().replace(' ', '_')\nprint(u)",
        "run_all": True
    }, headers=student_headers)
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["all_passed"] is True
    # At least one hidden test is present and its expected output is masked
    hidden_items = [t for t in d3["results"] if not t["is_public"]]
    assert len(hidden_items) >= 1
    assert hidden_items[0]["expected_output"] == "[Protégé]"
    assert hidden_items[0]["input"] == "[Test Caché]"

def test_grading_coding_evaluator_partial_credit():
    from backend.app.services.grading import evaluate_answer

    test_cases = [
        {"id": "t1", "input": "2\n", "expected_output": "4", "is_public": True},
        {"id": "t2", "input": "3\n", "expected_output": "9", "is_public": True},
        {"id": "t3", "input": "4\n", "expected_output": "16", "is_public": False}
    ]

    # 1. Full correct code
    perfect_code = "n = int(input())\nprint(n * n)"
    awarded, is_corr, fb = evaluate_answer("coding", perfect_code, test_cases, points=6.0)
    assert is_corr is True
    assert awarded == 6.0
    assert "3/3" in fb

    # 2. Code that only handles numbers < 4 (fails test 3)
    partial_code = "n = int(input())\nif n == 2: print(4)\nelif n == 3: print(9)\nelse: print(0)"
    awarded, is_corr, fb = evaluate_answer("coding", partial_code, test_cases, points=6.0)
    assert is_corr is False
    assert awarded == 4.0  # 2 out of 3 = 4.0 points
    assert "2/3" in fb

    # 3. Failing code (syntax error)
    broken_code = "def invalid syntax!"
    awarded, is_corr, fb = evaluate_answer("coding", broken_code, test_cases, points=6.0)
    assert is_corr is False
    assert awarded == 0.0

    # 4. Empty code
    awarded, is_corr, fb = evaluate_answer("coding", "", test_cases, points=6.0)
    assert is_corr is False
    assert awarded == 0.0

def test_curriculum_and_challenges_10_hidden_tests_requirement():
    import json, os
    
    # 1. Curriculum test counts
    curr_path = os.path.join("backend", "app", "data", "python_training", "curriculum.json")
    with open(curr_path, "r", encoding="utf-8") as f:
        curr = json.load(f)
        
    total_curr = 0
    for ch in curr["chapters"]:
        for ex in ch["coding_exercises"]:
            total_curr += 1
            assert len(ex.get("public_tests", [])) >= 2, f"Curriculum ex {ex['id']} has < 2 public tests"
            assert len(ex.get("hidden_tests", [])) >= 10, f"Curriculum ex {ex['id']} has < 10 hidden tests"
            
    assert total_curr == 333, f"Expected 333 curriculum exercises, found {total_curr}"
    
    # 2. Coding challenges test counts
    chal_path = os.path.join("backend", "app", "data", "python_training", "coding_challenges.json")
    with open(chal_path, "r", encoding="utf-8") as f:
        chal = json.load(f)
        
    assert len(chal) == 47, f"Expected 47 challenges, found {len(chal)}"
    for c in chal:
        assert len(c.get("public_tests", [])) >= 2, f"Challenge {c['id']} has < 2 public tests"
        assert len(c.get("hidden_tests", [])) >= 10, f"Challenge {c['id']} has < 10 hidden tests"

def test_matplotlib_graph_visualization_and_figure_capture():
    code = (
        "import matplotlib.pyplot as plt\n"
        "x = [1, 2, 3]\n"
        "y = [4, 5, 6]\n"
        "plt.plot(x, y)\n"
        "plt.title('Test Plot')\n"
        "print('Plot generated')\n"
    )
    res = execute_user_code_with_input(code, "", timeout_seconds=4.0)
    assert res["success"] is True
    assert "Plot generated" in res["stdout"]
    assert "figures" in res
    assert len(res["figures"]) >= 1
    assert res["figures"][0].startswith("data:image/png;base64,")



