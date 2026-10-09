"""Plinko optimization setup for the Rust weight-tuning algorithm.

Generates optimization parameters for all 27 BetModes (9 rows x 3 risks).
Each mode has a single "basegame" condition — every spin returns a payout,
so hit-rate is 1 (100%) and the full RTP sits in "basegame".
"""

from game_config import GameConfig, BASE_MULTIPLIERS, ROWS, RISKS, analytical_rtp
from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """Build opt_params for every Plinko (rows, risk) mode."""

    def __init__(self, game_config: GameConfig):
        self.game_config = game_config
        self.game_config.opt_params = {}

        for rows in ROWS:
            for risk in RISKS:
                name = f"{rows}_{risk}"
                mults = BASE_MULTIPLIERS[rows][risk]
                rtp = analytical_rtp(rows, mults)

                self.game_config.opt_params[name] = {
                    "conditions": {
                        "basegame": ConstructConditions(
                            rtp=round(rtp, 5),
                            hr=1,
                            av_win=round(rtp, 5),
                        ).return_dict(),
                    },
                    "scaling": ConstructScaling(
                        [
                            {
                                "criteria": "basegame",
                                "scale_factor": 1,
                                "win_range": (1, 1),
                                "probability": 1.0,
                            },
                        ]
                    ).return_dict(),
                    "parameters": ConstructParameters(
                        num_show=15000,
                        num_per_fence=20000,
                        min_m2m=2,
                        max_m2m=6,
                        pmb_rtp=1.0,
                        sim_trials=5000,
                        test_spins=[50, 100, 200],
                        test_weights=[0.3, 0.4, 0.3],
                        score_type="rtp",
                    ).return_dict(),
                }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
