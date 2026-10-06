"""Vice Cartel — pure math calculations."""

import random
from src.executables.executables import Executables
from src.calculations.lines import Lines
from src.calculations.statistics import get_random_outcome
from game_config import (
    WILD_MULTIPLIER_WEIGHTS, BLUE_INCREMENT_WEIGHTS, YELLOW_EXTRA_TURNS_WEIGHTS,
    SURVIVAL_DEAD_SPIN_PROB, WHEEL_TRIGGER_PROB, WHEEL_RED_WEIGHT, WHEEL_BLUE_WEIGHT,
    WHEEL_YELLOW_WEIGHT, RED_DOUBLE_WILD_PROB, MYSTERY_TRIGGER_PROB,
    MYSTERY_OUTCOME_WEIGHTS, PER_REEL_WILD_PROB, GOLDEN_CASE_LETTER_PROB,
)


class GameCalculations(Executables):

    @staticmethod
    def is_reel_wild(prob: float = PER_REEL_WILD_PROB) -> bool:
        return random.random() < prob

    @staticmethod
    def draw_wild_multiplier() -> int:
        return get_random_outcome(WILD_MULTIPLIER_WEIGHTS)

    @staticmethod
    def compute_spin_multiplier(wild_reels: dict[int, int]) -> int:
        return sum(wild_reels.values()) if wild_reels else 1

    @staticmethod
    def evaluate_lines(board, config, global_multiplier: int = 1) -> dict:
        return Lines.get_lines(board, config, global_multiplier=global_multiplier)

    @staticmethod
    def count_scatter(board, num_reels: int, num_rows: list[int]) -> int:
        count = 0
        for reel in range(num_reels):
            for row in range(num_rows[reel]):
                if board[reel][row].name == "SC":
                    count += 1
        return count

    @staticmethod
    def get_scatter_payout(count: int, scatter_pay: dict) -> float:
        if count >= 5:
            return scatter_pay.get(5, 0.0)
        return scatter_pay.get(count, 0.0)

    @staticmethod
    def mystery_check(trigger_prob: float = MYSTERY_TRIGGER_PROB) -> str | None:
        if random.random() >= trigger_prob:
            return None
        return get_random_outcome(MYSTERY_OUTCOME_WEIGHTS)

    @staticmethod
    def wheel_triggers() -> bool:
        return random.random() < WHEEL_TRIGGER_PROB

    @staticmethod
    def wheel_segment() -> str:
        return get_random_outcome({"RED": WHEEL_RED_WEIGHT, "BLUE": WHEEL_BLUE_WEIGHT, "YELLOW": WHEEL_YELLOW_WEIGHT})

    @staticmethod
    def red_wild_count() -> int:
        return 2 if random.random() < RED_DOUBLE_WILD_PROB else 1

    @staticmethod
    def blue_increment() -> int:
        return get_random_outcome(BLUE_INCREMENT_WEIGHTS)

    @staticmethod
    def yellow_extra_turns() -> int:
        return get_random_outcome(YELLOW_EXTRA_TURNS_WEIGHTS)

    @staticmethod
    def is_dead_spin(wild_count: int) -> bool:
        prob = SURVIVAL_DEAD_SPIN_PROB.get(min(wild_count, 5), 0.0)
        return random.random() < prob

    @staticmethod
    def golden_case_spin() -> tuple[int, bool]:
        """Roll 3 letters (M, A, X) independently, with at-least-1 guarantee."""
        q = GOLDEN_CASE_LETTER_PROB
        while True:
            letters = sum(1 for _ in range(3) if random.random() < q)
            if letters >= 1:
                return letters, letters == 3
