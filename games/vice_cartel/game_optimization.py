"""Vice Cartel — optimization setup for all 6 modes."""

from optimization_program.optimization_config import (
    ConstructScaling, ConstructParameters, ConstructConditions, verify_optimization_input,
)


def _default_params():
    """Shared optimizer parameters across modes."""
    return ConstructParameters(
        num_show=5000, num_per_fence=10000, min_m2m=4, max_m2m=8,
        pmb_rtp=1.0, sim_trials=5000, test_spins=[50, 100, 200],
        test_weights=[0.3, 0.4, 0.3], score_type="rtp",
    ).return_dict()


def _single_criteria_mode(criteria, rtp):
    """Pin a single-criteria mode to the target RTP, keeping its natural hit rate."""
    return {
        "conditions": {
            criteria: ConstructConditions(rtp=rtp, hr="x").return_dict(),
        },
        "scaling": ConstructScaling([
            {"criteria": criteria, "scale_factor": 1, "win_range": (1, 1), "probability": 1.0},
        ]).return_dict(),
        "parameters": _default_params(),
    }


class OptimizationSetup:

    def __init__(self, game_config):
        self.game_config = game_config
        rtp = game_config.rtp
        self.game_config.opt_params = {
            "base":            _single_criteria_mode("basegame", rtp),
            "golden_case":     _single_criteria_mode("golden_case", rtp),
            "extra_chance_3x": _single_criteria_mode("basegame", rtp),
            "extra_chance_5x": _single_criteria_mode("basegame", rtp),
            "min2wild_200x":   _single_criteria_mode("basegame", rtp),
            "min2wild_250x":   _single_criteria_mode("basegame", rtp),
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
