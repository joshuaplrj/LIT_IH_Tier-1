"""
MiniRust Parallel Compilation Pipeline
Contains 5 threading/concurrency bugs for the Self-Healing Compiler challenge.
"""

import threading
import queue
import time
from typing import List, Dict, Any, Optional
from lexer import tokenize
from parser import parse
from typechecker import typecheck
from codegen import codegen

# BUG_13: Barrier initialized with wrong count (2 instead of dynamic worker count)
# This causes permanent deadlock when more than 2 files are compiled in parallel.
_WRONG_BARRIER_COUNT = 2
_barrier = threading.Barrier(_WRONG_BARRIER_COUNT)  # BUG_13

# Shared symbol table — accessed without lock (BUG_11)
shared_symbol_table: Dict[str, Any] = {}  # BUG_11: no lock protecting this

# Results list — written from threads while main thread iterates (BUG_15)
compilation_results: List[Dict] = []  # BUG_15


def compile_single(source: str, filename: str) -> Dict:
    """Compile one MiniRust source file and return result dict."""
    try:
        tokens = tokenize(source)
        ast = parse(source)
        typecheck(ast)
        ir = codegen(ast)
        return {"file": filename, "status": "ok", "ir": ir}
    except Exception as e:
        return {"file": filename, "status": "error", "message": str(e)}


def worker_thread(task_queue: queue.Queue, result_queue: queue.Queue):
    """Worker: pull tasks from queue, compile, push results."""
    while True:
        try:
            item = task_queue.get(timeout=1)
        except queue.Empty:
            break

        source, filename = item

        # BUG_11: Writing to shared_symbol_table without holding any lock
        shared_symbol_table[filename] = "in_progress"  # BUG_11: race condition

        result = compile_single(source, filename)

        # BUG_11: Another unsynchronized write
        shared_symbol_table[filename] = result.get("status", "error")  # BUG_11

        try:
            # BUG_13: Barrier wait — blocks forever if more than 2 workers
            _barrier.wait(timeout=5)  # BUG_13
        except threading.BrokenBarrierError:
            pass

        # BUG_14: Exception in worker thread is silently caught and swallowed
        # The result_queue.put is inside a try-except that catches everything,
        # so if put() raises, the main thread will hang waiting for results.
        try:
            result_queue.put(result)
            if result["status"] == "error":
                raise RuntimeError(f"Compile error in {filename}")  # BUG_14: raised but caught below
        except Exception:
            pass  # BUG_14: Exception swallowed — main thread never gets result


def compile_parallel(sources: List[tuple], num_workers: int = 4) -> List[Dict]:
    """
    Compile multiple MiniRust files in parallel.
    sources: list of (source_code, filename) tuples
    Returns list of result dicts.
    """
    task_queue: queue.Queue = queue.Queue()
    result_queue: queue.Queue = queue.Queue()

    for item in sources:
        task_queue.put(item)

    threads = []
    for i in range(min(num_workers, len(sources))):
        # BUG_12: Classic Python closure bug — `i` is captured by reference in lambda.
        # All threads end up using the final value of `i`.
        t = threading.Thread(
            target=lambda: worker_thread(task_queue, result_queue),  # BUG_12: `i` not used here, but
            daemon=True                                               # see below for the captured-var pattern
        )
        # BUG_12 (full version): If we used `target=lambda idx=i: ...` it would be correct,
        # but the line below shows the buggy pattern applied to thread naming:
        t.name = (lambda: f"worker-{i}")()  # BUG_12: always captures last value of i
        threads.append(t)
        t.start()

    results = []
    expected = len(sources)
    received = 0

    # BUG_15: Main thread iterates compilation_results while worker appends to it.
    # This is a separate list from result_queue — workers append here directly.
    def background_collector():
        while received < expected:
            try:
                r = result_queue.get(timeout=0.5)
                compilation_results.append(r)  # BUG_15: append during potential iteration
            except queue.Empty:
                continue

    collector = threading.Thread(target=background_collector, daemon=True)
    collector.start()

    # BUG_15: Main thread iterates compilation_results while background_collector modifies it
    deadline = time.time() + 30
    while len(results) < expected and time.time() < deadline:
        for r in compilation_results:  # BUG_15: iterating list being modified concurrently
            if r not in results:
                results.append(r)
        time.sleep(0.05)

    for t in threads:
        t.join(timeout=2)

    return results
