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

from gamestate import GameState
from game_config import GameConfig, MODES, analytical_rtp
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
    """Print analytical RTP (per unit cost) for every mode."""
    print("\n" + "=" * 40)
    print("  Plinko Analytical RTP  (fair 50/50 per peg)")
    print("=" * 40)
    for name, spec in MODES.items():
        print(f"  {name:<12} cost {spec['cost']:<4} {analytical_rtp(name) * 100:>9.4f}%")
    print("=" * 40 + "\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # Show analytical RTP before simulation
    print_rtp_table()

    num_sim_args = {name: NUM_SIMS for name in MODES}

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
