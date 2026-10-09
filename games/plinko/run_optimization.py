"""Run ONLY the Rust-based weight optimization on existing lookup tables.

Skips simulation — reads the books/lookup_tables from the previous run
and optimizes weights to hit exact target RTP.

Usage (from the SDK root):
    python games/plinko/run_optimization.py
"""

import os
import sys

sdk_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, sdk_root)
sys.path.insert(0, os.path.join(sdk_root, "games", "plinko"))

from game_config import GameConfig, ROWS, RISKS
from gamestate import GameState
from game_optimization import OptimizationSetup
from src.write_data.write_configs import generate_configs
from optimization_program.run_script import OptimizationExecution

RUST_THREADS = 10

if __name__ == "__main__":
    config = GameConfig()
    gamestate = GameState(config)

    OptimizationSetup(config)
    generate_configs(gamestate)

    modes = [f"{rows}_{risk}" for rows in ROWS for risk in RISKS]
    print(f"Running Rust optimization for {len(modes)} modes...")

    failed = []
    for mode in modes:
        try:
            OptimizationExecution.run_opt_single_mode(config, mode, RUST_THREADS)
        except Exception as e:
            print(f"ERROR on mode {mode}: {e}")
            if hasattr(e, "stderr") and e.stderr:
                lines = e.stderr.strip().split("\n")
                err_lines = [l for l in lines if "ERROR" in l or "panic" in l.lower()]
                if err_lines:
                    print(f"  Rust error: {err_lines[-1]}")
            failed.append(mode)

    if failed:
        print(f"\n{len(failed)} modes failed: {failed}")
    else:
        print("\nAll modes optimized successfully.")
    print("\nOptimization complete.")
