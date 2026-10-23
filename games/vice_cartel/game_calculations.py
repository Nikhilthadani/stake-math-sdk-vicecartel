"""Vice Cartel — pure math calculations."""

import random
from src.executables.executables import Executables
from src.calculations.lines import Lines
from src.calculations.statistics import get_random_outcome
from game_config import (
    WILD_MULTIPLIER_WEIGHTS, BLUE_INCREMENT_WEIGHTS, YELLOW_EXTRA_TURNS_WEIGHTS,
    WHEEL_RED_WEIGHT, WHEEL_BLUE_WEIGHT, WHEEL_YELLOW_WEIGHT, RED_DOUBLE_WILD_PROB,
    PER_REEL_WILD_PROB, GOLDEN_CASE_LETTER_PROB, SCATTER_COUNT_PROBS, BONUS_TIERS,
)


_MULT_TOTAL = sum(WILD_MULTIPLIER_WEIGHTS.values())
_MULT_P = {m: w / _MULT_TOTAL for m, w in WILD_MULTIPLIER_WEIGHTS.items()}
_MAX_WILD_REELS = 5
_MAX_MULT_SUM = _MAX_WILD_REELS * max(_MULT_P)


def _build_sum_cdfs() -> list[list[float]]:
    """cdf[k][s] = P(sum of k Wild multipliers <= s)."""
    pmf = [1.0] + [0.0] * _MAX_MULT_SUM
    cdfs = []
    for k in range(_MAX_WILD_REELS + 1):
        acc, cdf = 0.0, []
        for p in pmf:
            acc += p
            cdf.append(acc)
        cdfs.append(cdf)
        nxt = [0.0] * (_MAX_MULT_SUM + 1)
        for s, p in enumerate(pmf):
            if p:
                for m, pm in _MULT_P.items():
                    if s + m <= _MAX_MULT_SUM:
                        nxt[s + m] += p * pm
        pmf = nxt
    return cdfs


_SUM_CDF = _build_sum_cdfs()


def mult_sum_range_prob(k: int, lo: int, hi: int) -> float:
    """P(lo <= sum of k Wild multipliers <= hi)."""
    lo, hi = max(lo, 0), min(hi, _MAX_MULT_SUM)
    if lo > hi:
        return 0.0
    cdf = _SUM_CDF[k]
    return cdf[hi] - (cdf[lo - 1] if lo > 0 else 0.0)


class GameCalculations(Executables):

    @staticmethod
    def is_reel_wild(prob: float = PER_REEL_WILD_PROB) -> bool:
        return random.random() < prob

    @staticmethod
    def draw_wild_multiplier() -> int:
        return get_random_outcome(WILD_MULTIPLIER_WEIGHTS)

    @staticmethod
    def draw_wild_multipliers_in_range(count: int, lo: int, hi: int) -> list[int]:
        """Draw `count` Wild multipliers from their exact joint distribution given lo <= sum <= hi."""
        mults = []
        for remaining in range(count, 0, -1):
            weights = {
                m: p * mult_sum_range_prob(remaining - 1, lo - m, hi - m) for m, p in _MULT_P.items()
            }
            m = get_random_outcome({m: w for m, w in weights.items() if w > 0})
            mults.append(m)
            lo, hi = lo - m, hi - m
        return mults

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
        return scatter_pay.get(count, 0.0)

    @staticmethod
    def draw_scatter_count(uplift: float = 1.0, forced=None) -> int:
        """Scatter count for one base spin; uplift multiplies P(3..6) and P(0) absorbs the difference.

        forced: an int fixes the count; "plain" draws from 0..2 in their natural proportions.
        """
        if isinstance(forced, int):
            return forced
        probs = {n: p * uplift if n >= 3 else p for n, p in SCATTER_COUNT_PROBS.items()}
        if forced == "plain":
            probs = {n: p for n, p in probs.items() if n < 3}
            probs[0] = 1.0 - sum(p * uplift if n >= 3 else p for n, p in SCATTER_COUNT_PROBS.items())
            return get_random_outcome(probs)
        u = random.random()
        acc = 0.0
        for n in sorted(probs):
            acc += probs[n]
            if u < acc:
                return n
        return 0

    @staticmethod
    def wheel_triggers(tier: str) -> bool:
        return random.random() < BONUS_TIERS[tier]["wheel_prob"]

    @staticmethod
    def wheel_segment(tier: str) -> str:
        return get_random_outcome({
            "RED": WHEEL_RED_WEIGHT,
            "BLUE": WHEEL_BLUE_WEIGHT,
            "YELLOW": WHEEL_YELLOW_WEIGHT,
            "MAX_WIN": BONUS_TIERS[tier]["maxwin_weight"],
        })

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
    def golden_case_spin() -> tuple[int, bool]:
        """Roll 3 letters (M, A, X) independently, with at-least-1 guarantee."""
        q = GOLDEN_CASE_LETTER_PROB
        while True:
            letters = sum(1 for _ in range(3) if random.random() < q)
            if letters >= 1:
                return letters, letters == 3
