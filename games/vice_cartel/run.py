"""Vice Cartel — simulation runner (natural stratified books, no optimizer)."""

import glob
import os
import sys
from gamestate import GameState
from game_config import GameConfig
from game_override import raw_wins_dir
from game_weights import apply_natural_weights
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 10
    batching_size = 1000
    compression = True
    profiling = False

    config = GameConfig()
    gamestate = GameState(config)

    # Book counts come from the fixed per-class amounts in game_config.py
    num_sim_args = {
        bm.get_name(): sum(d.get_fixed_amt() for d in bm.get_distributions()) for bm in config.bet_modes
    }

    run_conditions = {
        "run_sims": True,
        "run_weights": True,
        "run_analysis": False,
        "run_format_checks": True,
    }

    # Optional CLI mode list re-simulates only those modes; weighting always covers all
    sim_modes = {m: num_sim_args[m] for m in sys.argv[1:]} if len(sys.argv) > 1 else dict(num_sim_args)

    if run_conditions["run_sims"]:
        # A previous publish table or raw-win sidecar would point at the old books
        for mode in sim_modes:
            stale = [gamestate.output_files.get_optimized_lookup_name(mode)]
            stale += glob.glob(os.path.join(raw_wins_dir(gamestate), f"raw_{mode}_*.csv"))
            for path in stale:
                if os.path.exists(path):
                    os.remove(path)

        create_books(
            gamestate,
            config,
            sim_modes,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    if run_conditions["run_weights"]:
        apply_natural_weights(gamestate, list(num_sim_args))

    generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        create_stat_sheet(gamestate)

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)
