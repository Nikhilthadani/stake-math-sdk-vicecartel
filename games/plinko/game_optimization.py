"""Plinko optimization setup for the Rust weight-tuning algorithm.

Generates optimization parameters for all 20 BetModes.
Each mode has a single "basegame" condition — every drop returns a payout.
Base modes use hit-rate 1; wheel buy modes use hr="x" (buy-mode convention,
RTP measured against mode cost).
"""

from game_config import GameConfig, MODES, analytical_rtp
from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)


def _conditions(mode):
    rtp = round(analytical_rtp(mode), 5)
    if MODES[mode]["wheel_slots"]:
        return ConstructConditions(rtp=rtp, hr="x").return_dict()
    return ConstructConditions(rtp=rtp, hr=1, av_win=rtp).return_dict()


class OptimizationSetup:
    """Build opt_params for every Plinko mode."""

    def __init__(self, game_config: GameConfig):
        self.game_config = game_config
        self.game_config.opt_params = {
            mode: {
                "conditions": {"basegame": _conditions(mode)},
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
            for mode in MODES
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
