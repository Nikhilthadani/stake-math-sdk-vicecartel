"""Vice Cartel — optimization setup (placeholder for Phase 7)."""

from optimization_program.optimization_config import (
    ConstructScaling, ConstructParameters, ConstructConditions, verify_optimization_input,
)


class OptimizationSetup:

    def __init__(self, game_config):
        self.game_config = game_config
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "bonus": ConstructConditions(rtp=0.556, hr=984, search_conditions={"kind": "mystery"}).return_dict(),
                    "basegame": ConstructConditions(hr=3.0, rtp=0.403).return_dict(),
                },
                "scaling": ConstructScaling([
                    {"criteria": "basegame", "scale_factor": 1, "win_range": (1, 1), "probability": 1.0},
                    {"criteria": "bonus", "scale_factor": 1, "win_range": (1, 1), "probability": 1.0},
                ]).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000, num_per_fence=10000, min_m2m=4, max_m2m=8,
                    pmb_rtp=1.0, sim_trials=5000, test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3], score_type="rtp",
                ).return_dict(),
            },
        }
        verify_optimization_input(self.game_config, self.game_config.opt_params)
