"""Generate Plinko math files for Stake Engine.

Usage (from the SDK root):
    python games/plinko/run.py

Outputs go to games/plinko/library/:
    books/              Uncompressed simulation results (.json)
    books_compressed/   Compressed results for RGS (.jsonl.zst)
    lookup_tables/      CSV: sim_id, weight, payout_multiplier
    configs/            config.json, config_fe, index.json
    forces/             Force-record files
    publish_files/      Final files ready for Stake Engine upload
"""

import os
import sys

sdk_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, sdk_root)
sys.path.insert(0, os.path.join(sdk_root, "games", "plinko"))

from math import comb

from gamestate import GameState
from game_config import GameConfig, BASE_MULTIPLIERS, ROWS, RISKS
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution


# ─── Simulation settings ─────────────────────────────────────────────────────
# Start small (100) for testing. Use 100_000+ for production.

NUM_SIMS = 1000000
NUM_THREADS = 10
BATCHING_SIZE = 50000
COMPRESSION = True
PROFILING = False

# ─── Optimization settings ────────────────────────────────────────────────────
RUN_OPTIMIZATION = True
RUST_THREADS = 10


# ─── RTP validation ──────────────────────────────────────────────────────────

def print_rtp_table():
    """Print analytical RTP for every (rows, risk) configuration."""
    print("\n" + "=" * 60)
    print("  Plinko Analytical RTP  (fair 50/50 per peg)")
    print("=" * 60)
    header = f"  {'Rows':<6}"
    for risk in RISKS:
        header += f"{risk:>12}"
    print(header)
    print("  " + "-" * 42)

    for rows in ROWS:
        line = f"  {rows:<6}"
        for risk in RISKS:
            mults = BASE_MULTIPLIERS[rows][risk]
            ev = sum(comb(rows, k) * mults[k] for k in range(rows + 1))
            rtp = ev / (2 ** rows)
            line += f"{rtp * 100:>11.4f}%"
        print(line)

    print("=" * 60 + "\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Show analytical RTP before simulation
    print_rtp_table()

    # Build sim args for all 15 modes
    num_sim_args = {}
    for rows in ROWS:
        for risk in RISKS:
            num_sim_args[f"{rows}_{risk}"] = NUM_SIMS

    config = GameConfig()
    gamestate = GameState(config)

    # Run simulations
    create_books(
        gamestate,
        config,
        num_sim_args,
        BATCHING_SIZE,
        NUM_THREADS,
        COMPRESSION,
        PROFILING,
    )

    # Generate config files (config.json, config_fe, index.json)
    generate_configs(gamestate)

    # Run Rust-based weight optimization (tunes lookup table weights for exact target RTP)
    if RUN_OPTIMIZATION:
        OptimizationSetup(config)
        generate_configs(gamestate)
        modes_to_run = list(num_sim_args.keys())
        OptimizationExecution.run_all_modes(config, modes_to_run, RUST_THREADS)

    print("\nDone. Output files are in: games/plinko/library/")
    print("  Publish files (for Stake Engine upload): games/plinko/library/publish_files/")
