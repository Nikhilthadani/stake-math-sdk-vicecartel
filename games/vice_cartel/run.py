"""Vice Cartel — simulation runner."""

import os
from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 10
    rust_threads = 20
    batching_size = 5000
    compression = True
    profiling = False

    num_sim_args = {
        "base": int(1e6),
        "golden_case": int(1e6),
        "extra_chance_3x": int(1e6),
        "extra_chance_5x": int(1e6),
        "min2wild_200x": int(1e6),
        "min2wild_250x": int(1e6),
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": True,
        "run_analysis": True,
        "run_format_checks": True,
    }
    # Golden Case and Min 2 Wild publish their natural books unweighted (raw RTP is already in band)
    target_modes = ["base", "extra_chance_3x", "extra_chance_5x"]

    config = GameConfig()
    gamestate = GameState(config)

    if run_conditions.get("run_optimization") or run_conditions.get("run_analysis"):
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        # A previous publish table would point at the old books, and the SDK never overwrites it
        for mode in num_sim_args:
            stale_lookup = gamestate.output_files.get_optimized_lookup_name(mode)
            if os.path.exists(stale_lookup):
                os.remove(stale_lookup)

        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions.get("run_optimization"):
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions.get("run_analysis"):
        create_stat_sheet(gamestate)

    if run_conditions.get("run_format_checks"):
        execute_all_tests(config)
