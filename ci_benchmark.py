#!/usr/bin/env python3
"""
CI benchmark script for GitHub Actions.

Runs all levels matching a prefix filter with a single strategy.
Designed for use in a matrix build: strategy × batch.

Usage:
    python ci_benchmark.py -s bfs -f MAPF -o results-bfs-MAPF.md
    python ci_benchmark.py -s dfs -f SA -t 300
"""

import argparse
import glob
import os
import re
import subprocess
import sys
import time


# ── Configuration ────────────────────────────────────────────────────────────
LEVEL_DIR = "levels"
SERVER_JAR = "server.jar"
DEFAULT_TIMEOUT = 180
JAVA_XMX = "4g"
VALID_STRATEGIES = ["bfs", "dfs", "astar", "wastar", "greedy"]


# ── Helpers ──────────────────────────────────────────────────────────────────

def compile_client():
    """Compile the search client with javac."""
    print("Compiling searchclient/*.java ...")
    result = subprocess.run(
        ["javac", "searchclient/*.java"],
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: Compilation failed!")
        print(result.stderr)
        sys.exit(1)
    print("Compilation successful.\n")


def parse_output(output: str):
    """
    Parse combined stdout+stderr from the server / client for key metrics.

    Handles numbers with commas (e.g. 4,230,326).
    When multiple progress lines exist, keeps the last one.
    """
    solved = False
    solution_length = "-"
    solve_time = "-"
    memory = "-"
    expanded = "-"
    frontier_size = "-"
    generated = "-"

    for line in output.splitlines():
        if "Found solution of length" in line:
            solved = True
            try:
                solution_length = line.split("length")[1].strip().strip(".,").replace(",", "")
            except Exception:
                pass

        if "#Expanded:" in line:
            try:
                m_exp = re.search(r"#Expanded:\s*([\d,]+)", line)
                m_frt = re.search(r"#Frontier:\s*([\d,]+)", line)
                m_gen = re.search(r"#Generated:\s*([\d,]+)", line)
                m_time = re.search(r"Time:\s*([\d.]+)\s*s", line)
                if m_exp:
                    expanded = m_exp.group(1).replace(",", "")
                if m_frt:
                    frontier_size = m_frt.group(1).replace(",", "")
                if m_gen:
                    generated = m_gen.group(1).replace(",", "")
                if m_time:
                    solve_time = m_time.group(1)
            except Exception:
                pass

        if "Memory used:" in line:
            try:
                memory = line.split("Memory used:")[1].strip()
            except Exception:
                pass

        if "Unable to solve level" in line:
            solved = False

    return {
        "solved": solved,
        "solution_length": solution_length,
        "time": solve_time,
        "memory": memory,
        "expanded": expanded,
        "generated": generated,
    }


def run_level(level_path: str, strategy: str, timeout: int):
    """Run a single level through the server and return parsed metrics."""
    client_cmd = f"java -Xmx{JAVA_XMX} searchclient.SearchClient -{strategy}"
    cmd = [
        "java", "-jar", SERVER_JAR,
        "-l", level_path,
        "-c", client_cmd,
        "-t", str(timeout),
    ]

    level_name = os.path.basename(level_path)
    print(f"  {level_name:<40s}", end="", flush=True)

    wall_start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
        wall_time = time.time() - wall_start
        full_output = (result.stdout or "") + "\n" + (result.stderr or "")

        metrics = parse_output(full_output)

        if result.returncode != 0 and not metrics["solved"]:
            metrics["status"] = "❌ Error"
            print(f"  Error (exit {result.returncode})")
        elif metrics["solved"]:
            metrics["status"] = "✅ Solved"
            print(f"  Solved  len={metrics['solution_length']:>6s}  t={metrics['time']:>8s}s")
        else:
            metrics["status"] = "❌ No solution"
            print(f"  No solution  t={metrics['time']:>8s}s")

        metrics["wall_time"] = f"{wall_time:.1f}"
        return metrics

    except subprocess.TimeoutExpired:
        print(f"  ⏱️  Timeout (>{timeout}s)")
        return {
            "status": "⏱️ Timeout",
            "solved": False,
            "solution_length": "-",
            "time": f">{timeout}",
            "wall_time": f">{timeout}",
            "memory": "-",
            "expanded": "-",
            "generated": "-",
        }
    except Exception as e:
        print(f"  Exception: {e}")
        return {
            "status": "❌ Exception",
            "solved": False,
            "solution_length": "-",
            "time": "-",
            "wall_time": "-",
            "memory": "-",
            "expanded": "-",
            "generated": "-",
        }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CI benchmark runner (single strategy × batch)")
    parser.add_argument("-s", "--strategy", required=True,
                        choices=VALID_STRATEGIES, help="Search strategy")
    parser.add_argument("-f", "--filter", required=True,
                        help="Level filename prefix filter (e.g. SA, MA, MAPF)")
    parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Timeout per level in seconds (default: 180)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output markdown file (default: results-{strategy}-{filter}.md)")
    parser.add_argument("--compile", action="store_true",
                        help="Compile searchclient before running")
    args = parser.parse_args()

    if args.output is None:
        args.output = f"results-{args.strategy}-{args.filter}.md"

    print(f"{'=' * 60}")
    print(f"  MAvis Hospital CI Benchmark")
    print(f"  Strategy : {args.strategy}")
    print(f"  Filter   : {args.filter}")
    print(f"  Timeout  : {args.timeout}s per level")
    print(f"  Output   : {args.output}")
    print(f"{'=' * 60}\n")

    # ── Prerequisites ────────────────────────────────────────────────────
    if not os.path.exists(SERVER_JAR):
        print(f"ERROR: {SERVER_JAR} not found in {os.getcwd()}")
        sys.exit(1)

    if args.compile:
        compile_client()

    class_files = glob.glob("searchclient/*.class")
    if not class_files:
        print("ERROR: No .class files in searchclient/. Compile first:")
        print("  javac searchclient/*.java")
        print("  or run with --compile flag")
        sys.exit(1)

    # ── Discover levels ──────────────────────────────────────────────────
    pattern = os.path.join(LEVEL_DIR, "*.lvl")
    levels = sorted(glob.glob(pattern))
    levels = [l for l in levels if os.path.basename(l).startswith(args.filter)]

    if not levels:
        print(f"No levels found matching prefix '{args.filter}' in {LEVEL_DIR}/")
        sys.exit(1)

    print(f"Found {len(levels)} level(s).\n")

    # ── Run benchmark ────────────────────────────────────────────────────
    results = []
    solved_count = 0
    timeout_count = 0
    error_count = 0

    for lvl in levels:
        level_name = os.path.basename(lvl).replace(".lvl", "")
        metrics = run_level(lvl, args.strategy, args.timeout)
        results.append((level_name, metrics))
        if metrics["solved"]:
            solved_count += 1
        elif "Timeout" in metrics["status"]:
            timeout_count += 1
        else:
            error_count += 1

    # ── Generate markdown report ─────────────────────────────────────────
    lines = []
    lines.append(f"## {args.filter} — {args.strategy.upper()}\n")
    lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Strategy:** `{args.strategy}` | **Timeout:** {args.timeout}s | **Java Xmx:** {JAVA_XMX}  ")
    lines.append(f"**Score:** {solved_count}/{len(levels)} solved")
    if timeout_count:
        lines.append(f" | {timeout_count} timeout")
    if error_count:
        lines.append(f" | {error_count} error/unsolved")
    lines.append("\n")
    lines.append("| Level | Status | Solution Length | Time (s) | Generated | Memory |")
    lines.append("|-------|--------|-----------------|----------|-----------|--------|")

    for level_name, m in results:
        lines.append(
            f"| `{level_name}` "
            f"| {m['status']} "
            f"| {m['solution_length']} "
            f"| {m['time']} "
            f"| {m['generated']} "
            f"| {m['memory']} |"
        )

    lines.append("")

    report = "\n".join(lines) + "\n"

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n{'=' * 60}")
        print(f"  Results saved to {args.output}")
        print(f"  Score: {solved_count}/{len(levels)} solved")
        print(f"{'=' * 60}")
    except Exception as e:
        print(f"ERROR writing results file: {e}")
        sys.exit(1)

    if solved_count < len(levels):
        sys.exit(1)


if __name__ == "__main__":
    main()
