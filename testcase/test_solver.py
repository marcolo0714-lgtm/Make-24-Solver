#!/usr/bin/env python3
"""
Test script for 24solver.py and 24solver.c.
Reads test cases from test_cases.txt, runs both solvers, and writes a
detailed report to report.txt while printing a compact summary to console.
"""

import subprocess
import sys
import os
import re
import math
import io
from typing import List, Tuple, Optional, NamedTuple, TextIO
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths  (script lives in testcase/, solvers live in parent dir)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
PY_SOLVER = ROOT / "24solver.py"
C_SOLVER  = ROOT / "24solver.c"
CASE_FILE = Path(__file__).resolve().parent / "test_cases.txt"
REPORT    = Path(__file__).resolve().parent / "report.txt"

# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RST    = "\033[0m"

TOLERANCE = 1e-9

_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}

# ---------------------------------------------------------------------------
# Test case definition
# ---------------------------------------------------------------------------
class TestCase(NamedTuple):
    idx: int
    numbers: List[int]
    target: int
    description: str
    solvable: bool
    all_solutions: bool


def load_test_cases(path: Path) -> List[TestCase]:
    """Parse test cases from the pipe-delimited text file."""
    cases: List[TestCase] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = [p.strip() for p in stripped.split("|")]
            if len(parts) != 5:
                continue
            numbers_str, target_str, solvable_str, all_str, desc = parts
            numbers = [int(n) for n in numbers_str.split()]
            target = int(target_str)
            solvable = solvable_str.lower() == "y"
            all_sol = all_str.lower() == "y"
            cases.append(TestCase(
                idx=len(cases) + 1,
                numbers=numbers,
                target=target,
                description=desc,
                solvable=solvable,
                all_solutions=all_sol,
            ))
    return cases


# ---------------------------------------------------------------------------
# Output parsing helpers
# ---------------------------------------------------------------------------
def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text).replace("\r", "")


def _remove_tqdm_lines(text: str) -> str:
    kept: List[str] = []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if "Processing permutations:" in s:
            continue
        if "it/s" in s or "s/it" in s:
            continue
        kept.append(line)
    return "\n".join(kept)


def _extract_exec_time(output: str) -> Optional[float]:
    m = re.search(r"Execution Time.*?([\d.]+)\s*seconds", output)
    return float(m.group(1)) if m else None


def _parse_py_first_solution(cleaned: str) -> Optional[str]:
    lines = cleaned.strip().split("\n")
    for i, line in enumerate(lines):
        if "Possible solution found" in line:
            for j in range(i + 1, len(lines)):
                cand = lines[j].strip()
                if not cand:
                    continue
                if re.match(r"^\(?\d", cand) or cand.startswith("(") or cand.startswith("-"):
                    return cand
    return None


def _parse_py_all_solutions(cleaned: str) -> List[str]:
    solutions: List[str] = []
    for line in cleaned.strip().split("\n"):
        m = re.match(r"^\s*(\d+):\s*(.+)$", line.strip())
        if m:
            solutions.append(m.group(2).strip())
    return solutions


def _parse_c_solutions(raw: str) -> List[str]:
    solutions: List[str] = []
    for line in raw.strip().split("\n"):
        m = re.search(r"\d+:\s*(.+?)\s*=\s*[-+]?[\d.]+", line)
        if m:
            solutions.append(m.group(1).strip())
    return solutions


def _has_solution_py(cleaned: str) -> bool:
    return "Possible solution found" in cleaned or "All possible solutions found" in cleaned


def _has_solution_c(raw: str) -> bool:
    return bool(re.search(r"\d+:\s*(.+?)\s*=\s*[-+]?[\d.]+", raw))


def _has_crash(text: str) -> bool:
    return "Traceback (most recent call last)" in text


# ---------------------------------------------------------------------------
# Expression evaluation
# ---------------------------------------------------------------------------
def _eval_expr(expr: str) -> Optional[float]:
    try:
        return eval(expr)
    except Exception:
        return None


def _close_enough(value: float, target: float) -> bool:
    return abs(value - target) <= TOLERANCE


# ---------------------------------------------------------------------------
# Compile C solver
# ---------------------------------------------------------------------------
def _compile_c_solver() -> Optional[str]:
    if not C_SOLVER.exists():
        return None

    exe_name = "24solver.exe" if sys.platform == "win32" else "24solver"
    exe_path = ROOT / exe_name

    compiler: Optional[str] = None
    for cc in ("gcc", "clang"):
        try:
            subprocess.run([cc, "--version"], capture_output=True,
                           check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            compiler = cc
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    if compiler is None:
        return None

    if exe_path.exists():
        if exe_path.stat().st_mtime > C_SOLVER.stat().st_mtime:
            return str(exe_path.resolve())

    result = subprocess.run(
        [compiler, "-std=c11", "-O2", str(C_SOLVER), "-o", str(exe_path)],
        capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        return None

    return str(exe_path.resolve())


# ---------------------------------------------------------------------------
# Run a solver subprocess
# ---------------------------------------------------------------------------
def _run(cmd: List[str], numbers: List[int], target: int,
         all_solutions: bool, timeout: int = 120,
         use_utf8_env: bool = False) -> Tuple[str, str, bool, Optional[float]]:
    """
    Launch solver, feed input via stdin.
    Returns (stdout, stderr, timed_out, exec_time_seconds).
    """
    inp = " ".join(str(n) for n in numbers) + "\n" + str(target) + "\n"
    inp += "y\n" if all_solutions else "n\n"

    kwargs = dict(
        input=inp,
        capture_output=True,
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if use_utf8_env:
        kwargs["encoding"] = "utf-8"
        kwargs["errors"] = "replace"
        kwargs["env"] = _UTF8_ENV
    else:
        kwargs["text"] = True

    try:
        result = subprocess.run(cmd, **kwargs)
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        return result.stdout or "", result.stderr or "", False, _extract_exec_time(combined)
    except subprocess.TimeoutExpired:
        return "", "", True, None
    except Exception as exc:
        return "", str(exc), False, None


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------
def _fmt_time(t: Optional[float]) -> str:
    if t is None:
        return "  N/A  "
    return f"{t:7.4f}s"


def main() -> int:
    # ---- load cases ----
    if not CASE_FILE.exists():
        print(f"{RED}FAIL: {CASE_FILE} not found{RST}")
        return 1

    test_cases = load_test_cases(CASE_FILE)
    if not test_cases:
        print(f"{RED}FAIL: no test cases loaded from {CASE_FILE}{RST}")
        return 1

    # ---- prerequisites ----
    if not PY_SOLVER.exists():
        print(f"{RED}FAIL: {PY_SOLVER} not found{RST}")
        return 1

    c_binary = _compile_c_solver()
    if c_binary is None:
        print(f"{RED}FAIL: Could not compile C solver. Stopping.{RST}")
        return 1

    try:
        import tqdm  # noqa: F401
    except ImportError:
        print(f"{RED}FAIL: tqdm not installed.  Run: pip install tqdm{RST}")
        return 1

    # ---- run tests ----
    passed = 0
    failed = 0
    failures: List[Tuple[int, str, str]] = []  # (idx, description, error_msg)
    report_lines: List[str] = []

    report_lines.append(f"{'='*70}")
    report_lines.append(f"  24 Solver Test Suite  —  Report")
    report_lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"{'='*70}")
    report_lines.append("")

    # Column widths for console alignment
    PER_ROW = 10

    for tc in test_cases:
        idx = tc.idx
        nums_str = " ".join(str(n) for n in tc.numbers)
        header = (f"[{idx:2d}] {tc.description}  "
                  f"(nums=[{nums_str}]  target={tc.target})")
        desc_line = f"{' '*(5 if idx < 10 else 4)}n={len(tc.numbers)}: {tc.description}"
        nums_line = f"{' '*(5 if idx < 10 else 4)}nums=[{nums_str}]  target={tc.target}"

        # ================================================================
        #  First-solution mode
        # ================================================================
        py_timeout = 120 if len(tc.numbers) >= 5 else 60
        py_stdout, py_stderr, py_to, py_t1 = _run(
            ["python", str(PY_SOLVER)], tc.numbers, tc.target,
            all_solutions=False, timeout=py_timeout, use_utf8_env=True,
        )
        c_stdout, c_stderr, c_to, c_t1 = _run(
            [c_binary], tc.numbers, tc.target,
            all_solutions=False, timeout=60,
        )

        error_msg: Optional[str] = None
        py_all_count = 0
        c_all_count = 0
        py_t2: Optional[float] = None
        c_t2: Optional[float] = None
        mode_label = "first-only" if not tc.all_solutions else ""

        if py_to or c_to:
            error_msg = f"TIMEOUT (py={py_to} c={c_to})"
        elif _has_crash(py_stdout + py_stderr):
            error_msg = "Python solver crashed"
        else:
            py_comb = py_stdout + "\n" + py_stderr
            c_comb = c_stdout + "\n" + c_stderr

            py_clean = _remove_tqdm_lines(_strip_ansi(py_comb))

            py_has = _has_solution_py(py_clean)
            c_has = _has_solution_c(c_comb)

            if py_has != c_has:
                error_msg = (f"SOLVABILITY MISMATCH: "
                             f"py={'SOL' if py_has else 'NOSOL'}  "
                             f"c={'SOL' if c_has else 'NOSOL'}")
            elif py_has != tc.solvable:
                error_msg = (f"WRONG RESULT: expected "
                             f"{'SOL' if tc.solvable else 'NOSOL'}, "
                             f"got {'SOL' if py_has else 'NOSOL'}")
            elif tc.solvable:
                py_expr = _parse_py_first_solution(py_clean)
                c_exprs = _parse_c_solutions(c_comb)

                if py_expr is None:
                    error_msg = "Parse fail (py first-solution)"
                elif c_exprs is None or len(c_exprs) == 0:
                    error_msg = "Parse fail (c first-solution)"
                else:
                    py_val = _eval_expr(py_expr)
                    if py_val is None or not _close_enough(py_val, tc.target):
                        error_msg = (f"Py first-solution wrong: "
                                     f"'{py_expr}' = {py_val}  "
                                     f"(expected {tc.target})")
                    else:
                        c_val = _eval_expr(c_exprs[0])
                        if c_val is None or not _close_enough(c_val, tc.target):
                            error_msg = (f"C first-solution wrong: "
                                         f"'{c_exprs[0]}' = {c_val}  "
                                         f"(expected {tc.target})")

            # ---- All-solutions mode ----
            if error_msg is None and tc.all_solutions:
                py_a_out, py_a_stderr, py_all_to, py_t2 = _run(
                    ["python", str(PY_SOLVER)], tc.numbers, tc.target,
                    all_solutions=True, timeout=120, use_utf8_env=True,
                )
                c_a_out, c_a_stderr, c_all_to, c_t2 = _run(
                    [c_binary], tc.numbers, tc.target,
                    all_solutions=True, timeout=120,
                )

                if py_all_to or c_all_to:
                    error_msg = "TIMEOUT in all-solutions mode"
                elif _has_crash(py_a_out + py_a_stderr):
                    error_msg = "Python crashed in all-solutions mode"
                else:
                    py_a_comb = py_a_out + "\n" + py_a_stderr
                    c_a_comb = c_a_out + "\n" + c_a_stderr
                    py_all_sols = _parse_py_all_solutions(
                        _remove_tqdm_lines(_strip_ansi(py_a_comb)))
                    c_all_sols = _parse_c_solutions(c_a_comb)
                    py_all_count = len(py_all_sols)
                    c_all_count = len(c_all_sols)

                    # Verify each Python solution
                    for expr in py_all_sols:
                        v = _eval_expr(expr)
                        if v is None or not _close_enough(v, tc.target):
                            error_msg = f"Py all-sol eval fail: '{expr}' -> {v}"
                            break
                    # Verify each C solution
                    if error_msg is None:
                        for expr in c_all_sols:
                            v = _eval_expr(expr)
                            if v is None or not _close_enough(v, tc.target):
                                error_msg = f"C all-sol eval fail: '{expr}' -> {v}"
                                break

                    if error_msg is None:
                        if tc.solvable and py_all_count == 0:
                            error_msg = "Py all-solutions returned 0 (should be solvable)"
                        elif tc.solvable and c_all_count == 0:
                            error_msg = "C all-solutions returned 0 (should be solvable)"

                mode_label = f"all(Py={py_all_count} C={c_all_count})"

        # ---- record result ----
        if error_msg is None:
            passed += 1
            status = "PASS"
            report_status = f"{GREEN}{status}{RST}"
        else:
            failed += 1
            status = "FAIL"
            report_status = f"{RED}{status}{RST}"
            failures.append((idx, tc.description, error_msg))

        # ---- console output ----
        mark = f"{GREEN}+{RST}" if status == "PASS" else f"{RED}-{RST}"
        end_char = "\n" if idx % PER_ROW == 0 else "  "
        print(f"[{idx:2d}] {mark}", end=end_char, flush=True)

        # ---- report line ----
        times = f"Py first: {_fmt_time(py_t1)} | C first: {_fmt_time(c_t1)}"
        if tc.all_solutions:
            times += f"\n     Py all:   {_fmt_time(py_t2)} ({py_all_count}) | C all:   {_fmt_time(c_t2)} ({c_all_count})"
        else:
            times += f"\n     (all-solutions skipped for n={len(tc.numbers)})"

        rpt = f"[{idx:2d}] {status:4s}  {tc.description}\n" \
              f"     nums=[{nums_str}]  target={tc.target}\n" \
              f"     {times}"
        if error_msg:
            rpt += f"\n     {RED}Error: {error_msg}{RST}"
        report_lines.append(rpt)
        report_lines.append("")

    # ---- final newline after progress dots ----
    if len(test_cases) % PER_ROW != 0:
        print()

    # ---- console summary ----
    total = passed + failed
    print(f"\n{BOLD}{'='*30}{RST}")
    if failed == 0:
        print(f"{GREEN}{total}/{total} passed{RST}")
    else:
        print(f"{GREEN}{passed}{RST}/{total} passed")
        print(f"\n{BOLD}Failed:{RST}")
        for idx, desc, err in failures:
            print(f"  {RED}[{idx:2d}]{RST} {desc}")
            print(f"       {RED}{err}{RST}")

    report_path = str(REPORT.resolve())
    print(f"\nReport: ", end="")
    try:
        print(report_path)
    except UnicodeEncodeError:
        print(report_path.encode("ascii", errors="replace").decode("ascii"))

    # ---- write report ----
    report_lines.append(f"{'='*70}")
    report_lines.append(f"  Results: {passed}/{total} passed")
    report_lines.append(f"{'='*70}")

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(_strip_ansi("\n".join(report_lines)) + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
