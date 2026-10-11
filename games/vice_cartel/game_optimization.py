"""Vice Cartel — optimization setup for all 6 modes."""

from optimization_program.optimization_config import (
    ConstructScaling, ConstructParameters, ConstructConditions, verify_optimization_input,
)
from game_config import (
    BASE_ONLY_RTP, BASE_HIT_RATE, MYSTERY_OUTCOME_WEIGHTS,
    MYSTERY_TRIGGER_PROB, MYSTERY_TRIGGER_PROB_EXTRA_3X, MYSTERY_TRIGGER_PROB_EXTRA_5X,
)

# Share of mystery checks that award a bonus tier
_BONUS_SHARE = 1 - MYSTERY_OUTCOME_WEIGHTS["no_bonus"] / sum(MYSTERY_OUTCOME_WEIGHTS.values())


def _default_params():
    """Shared optimizer parameters across modes."""
    return ConstructParameters(
        num_show=5000, num_per_fence=10000, min_m2m=4, max_m2m=8,
        pmb_rtp=1.0, sim_trials=5000, test_spins=[50, 100, 200],
        test_weights=[0.3, 0.4, 0.3], score_type="rtp",
    ).return_dict()


def _no_op_scaling(criteria):
    return ConstructScaling([
        {"criteria": criteria, "scale_factor": 1, "win_range": (1, 1), "probability": 1.0},
    ]).return_dict()


def _single_criteria_mode(criteria, rtp):
    """Pin a single-criteria mode to the target RTP, keeping its natural hit rate."""
    return {
        "conditions": {criteria: ConstructConditions(rtp=rtp, hr="x").return_dict()},
        "scaling": _no_op_scaling(criteria),
        "parameters": _default_params(),
    }


def _mystery_mode(rtp, cost, trigger_prob):
    """Fix bonus and base-win frequencies at their natural values; zero-win books take the remainder.

    "freegame" must precede "0" so zero-paying bonus books stay in the bonus fence.
    """
    base_rtp = round(BASE_ONLY_RTP / cost, 5)
    return {
        "conditions": {
            "freegame": ConstructConditions(
                rtp=round(rtp - base_rtp, 5),
                hr=round(1 / (trigger_prob * _BONUS_SHARE), 2),
                search_conditions={"kind": "mystery"},
            ).return_dict(),
            "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
            "basegame": ConstructConditions(rtp=base_rtp, hr=BASE_HIT_RATE).return_dict(),
        },
        "scaling": _no_op_scaling("basegame"),
        "parameters": _default_params(),
    }


class OptimizationSetup:

    def __init__(self, game_config):
        self.game_config = game_config
        rtp = game_config.rtp
        self.game_config.opt_params = {
            "base":            _mystery_mode(rtp, 1, MYSTERY_TRIGGER_PROB),
            "golden_case":     _single_criteria_mode("golden_case", rtp),
            "extra_chance_3x": _mystery_mode(rtp, 3, MYSTERY_TRIGGER_PROB_EXTRA_3X),
            "extra_chance_5x": _mystery_mode(rtp, 5, MYSTERY_TRIGGER_PROB_EXTRA_5X),
            "min2wild_200x":   _single_criteria_mode("basegame", rtp),
            "min2wild_250x":   _single_criteria_mode("basegame", rtp),
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
