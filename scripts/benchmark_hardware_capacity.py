import os
import sys
sys.path.insert(0, ".")
import time
import sqlite3
import concurrent.futures
from backend.app.services.sandbox_runner import execute_user_code_with_input

def benchmark_sqlite_wal(concurrency_levels=[10, 30, 50, 100]):
    print("=== 1. Benchmark SQLite WAL Concurrency (Autosaves) ===")
    db_path = "backend/benchmark_wal.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("CREATE TABLE answers (student_id TEXT, q_id TEXT, ans TEXT, ts REAL);")
    conn.commit()
    conn.close()

    def student_worker(s_id, num_saves=5):
        c = sqlite3.connect(db_path, timeout=10.0)
        c.execute("PRAGMA journal_mode=WAL;")
        for q in range(num_saves):
            c.execute("INSERT INTO answers VALUES (?, ?, ?, ?)", (f"student_{s_id}", f"Q_{q}", "my answer", time.time()))
            c.commit()
        c.close()
        return True

    results = {}
    for conc in concurrency_levels:
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=conc) as executor:
            futures = [executor.submit(student_worker, i) for i in range(conc)]
            for f in concurrent.futures.as_completed(futures):
                f.result()
        elapsed = time.perf_counter() - start
        total_writes = conc * 5
        ops_sec = round(total_writes / elapsed, 1)
        results[conc] = (round(elapsed, 3), ops_sec)
        print(f"  {conc} simultaneous students (total {total_writes} writes): {elapsed:.2f}s ({ops_sec} saves/sec)")

    if os.path.exists(db_path):
        try: os.remove(db_path)
        except: pass
    return results

def benchmark_sandbox_concurrency(concurrency_levels=[5, 10, 20, 30]):
    print("\n=== 2. Benchmark Python Sandbox Concurrency (Code Execution) ===")
    code = "import sys\nlines = sys.stdin.read().split()\nif lines: print(sum(int(x) for x in lines))"
    inp = "1 2 3 4 5 6 7 8 9 10\n"

    results = {}
    for conc in concurrency_levels:
        start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=conc) as executor:
            futures = [executor.submit(execute_user_code_with_input, code, inp, 3.0) for _ in range(conc)]
            successes = 0
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res.get("success"):
                    successes += 1
        elapsed = time.perf_counter() - start
        rps = round(conc / elapsed, 1)
        results[conc] = (round(elapsed, 3), successes, rps)
        print(f"  {conc} concurrent student code runs: {elapsed:.2f}s ({rps} runs/sec) - {successes}/{conc} successful")

    return results

if __name__ == "__main__":
    benchmark_sqlite_wal([10, 30, 50, 100])
    benchmark_sandbox_concurrency([5, 10, 15, 20, 30])
