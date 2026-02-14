#!/usr/bin/env python3
"""
Benchmark script for the MAvis Hospital search client.

Usage:
    python run_benchmark.py                         # Run all levels with default strategy (bfs)
    python run_benchmark.py -s greedy               # Use greedy strategy
    python run_benchmark.py -s astar -t 300         # A* with 5-min timeout
    python run_benchmark.py -f MAPF                 # Only run MAPF levels
    python run_benchmark.py -f SA -s greedy         # Only SA levels with greedy
    python run_benchmark.py --compile               # Compile before running
"""

import argparse
import glob
import os
import subprocess
import sys
import time


# ── Configuration ────────────────────────────────────────────────────────────
LEVEL_DIR = "levels"
OUTPUT_FILE = "benchmark_results.md"
SERVER_JAR = "server.jar"
DEFAULT_TIMEOUT = 180          # seconds per level
JAVA_XMX = "4g"
DEFAULT_STRATEGY = "bfs"
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

    Looks for:
        Found solution of length <N>.          (client stderr)
        #Expanded: … #Frontier: … Time: …     (client stderr)
        Memory used: …                         (client stderr)
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
                parts = line.split(",")
                for p in parts:
                    p = p.strip()
                    if p.startswith("#Expanded:"):
                        expanded = p.split(":")[1].strip().replace(",", "")
                    elif p.startswith("#Frontier:"):
                        frontier_size = p.split(":")[1].strip().replace(",", "")
                    elif p.startswith("#Generated:"):
                        generated = p.split(":")[1].strip().replace(",", "")
                    elif p.startswith("Time:"):
                        solve_time = p.split(":")[1].strip().replace("s", "").strip()
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
            timeout=timeout + 10,      # extra grace period
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
    parser = argparse.ArgumentParser(description="MAvis Hospital benchmark runner")
    parser.add_argument("-s", "--strategy", default=DEFAULT_STRATEGY,
                        choices=VALID_STRATEGIES, help="Search strategy (default: bfs)")
    parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Timeout per level in seconds (default: 180)")
    parser.add_argument("-f", "--filter", default=None,
                        help="Only run levels whose filename starts with this prefix (e.g. SA, MA, MAPF)")
    parser.add_argument("-o", "--output", default=OUTPUT_FILE,
                        help="Output markdown file (default: benchmark_results.md)")
    parser.add_argument("--compile", action="store_true",
                        help="Compile searchclient before running")
    args = parser.parse_args()

    print(f"{'=' * 60}")
    print(f"  MAvis Hospital Benchmark")
    print(f"  Strategy : {args.strategy}")
    print(f"  Timeout  : {args.timeout}s per level")
    print(f"  Filter   : {args.filter or 'all levels'}")
    print(f"  CWD      : {os.getcwd()}")
    print(f"  Python   : {sys.version.split()[0]}")
    print(f"{'=' * 60}\n")

    # ── Prerequisites ────────────────────────────────────────────────────
    if not os.path.exists(SERVER_JAR):
        print(f"ERROR: {SERVER_JAR} not found in {os.getcwd()}")
        sys.exit(1)

    if args.compile:
        compile_client()

    # Check that .class files exist
    class_files = glob.glob("searchclient/*.class")
    if not class_files:
        print("ERROR: No .class files in searchclient/. Compile first:")
        print("  javac searchclient/*.java")
        print("  or run with --compile flag")
        sys.exit(1)

    # ── Discover levels ──────────────────────────────────────────────────
    pattern = os.path.join(LEVEL_DIR, "*.lvl")
    levels = sorted(glob.glob(pattern))

    if args.filter:
        levels = [l for l in levels if os.path.basename(l).startswith(args.filter)]

    if not levels:
        print(f"No levels found matching pattern in {LEVEL_DIR}/")
        sys.exit(1)

    print(f"Found {len(levels)} level(s).\n")

    # ── Run benchmark ────────────────────────────────────────────────────
    results = []        # list of (level_name, metrics_dict)
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
    lines.append(f"# Benchmark Results\n")
    lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Strategy:** `{args.strategy}` | **Timeout:** {args.timeout}s | **Java Xmx:** {JAVA_XMX}  ")
    lines.append(f"**Score:** {solved_count}/{len(levels)} solved")
    if timeout_count:
        lines.append(f" | {timeout_count} timeout")
    if error_count:
        lines.append(f" | {error_count} error/unsolved")
    lines.append("\n")
    lines.append("| Level | Status | Solution Length | Time (s) | Expanded | Generated | Memory |")
    lines.append("|-------|--------|-----------------|----------|----------|-----------|--------|")

    for level_name, m in results:
        lines.append(
            f"| `{level_name}` "
            f"| {m['status']} "
            f"| {m['solution_length']} "
            f"| {m['time']} "
            f"| {m['expanded']} "
            f"| {m['generated']} "
            f"| {m['memory']} |"
        )

    lines.append("")
    lines.append("### Summary")
    lines.append(f"- **Total**: {len(levels)}")
    lines.append(f"- **Solved**: {solved_count} ✅")
    lines.append(f"- **Timeout**: {timeout_count} ⏱️")
    lines.append(f"- **Error / Unsolved**: {error_count} ❌")

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

    # Return non-zero if any level failed (useful for CI)
    if solved_count < len(levels):
        sys.exit(1)


if __name__ == "__main__":
    main()
