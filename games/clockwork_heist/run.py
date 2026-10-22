"""Generate Clockwork Heist math files for Stake Engine.

Usage (from the SDK root):
    python games/clockwork_heist/run.py

Outputs go to games/clockwork_heist/library/ (books, lookup tables, configs, publish_files).
"""

import csv
import math
import os
import sys
from fractions import Fraction

sdk_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, sdk_root)
sys.path.insert(0, os.path.join(sdk_root, "games", "clockwork_heist"))

from check_parity import PAR  # noqa: E402
from gamestate import GameState  # noqa: E402
from game_config import SCATTER, GameConfig  # noqa: E402
from src.state.run_sims import create_books  # noqa: E402
from src.write_data.write_configs import generate_configs  # noqa: E402

NUM_THREADS = 10
RUST_THREADS = 20
BATCHING_SIZE = 5000
COMPRESSION = True
PROFILING = False

NUM_SIM_ARGS = {
    "base": int(1e4),
    "bonus": int(1e4),
    "mwon": int(1e4),
}

RUN_CONDITIONS = {
    "run_sims": True,
    "run_optimization": False,
    "run_analysis": False,
    "run_format_checks": False,
}


MWON_MODE = "mwon"
BASE_MODE = "base"
BASE_WEIGHT_TOTAL = 10**15
TILTED_MODES = ("base", "bonus")
# Equal-weight tables are scaled up first so integer rounding of the tilt stays below 1e-9
TILT_MIN_WEIGHT = 10**9


def trigger_probability(config) -> Fraction:
    """Exact P(free spins trigger) on the BR0 board, from each reel's scatters-per-window distribution."""
    rows = config.num_rows[0]
    needed = min(config.freespin_triggers[config.basegame_type].keys())
    totals = {0: Fraction(1)}
    for strip in config.reels["BR0"]:
        n = len(strip)
        per_window = {}
        for stop in range(n):
            count = sum(strip[(stop + k) % n] == SCATTER for k in range(rows))
            per_window[count] = per_window.get(count, 0) + 1
        merged = {}
        for total, p in totals.items():
            for count, windows in per_window.items():
                merged[total + count] = merged.get(total + count, 0) + p * Fraction(windows, n)
        totals = merged
    return sum(p for total, p in totals.items() if total >= needed)


def set_base_weights(gamestate) -> None:
    """Weights the base lookup table by natural criteria odds instead of the forced book quotas.

    P(freegame) is the exact trigger probability of the base reels; every triggered round pays
    (10x minimum), so P(basegame) is the PAR hit rate minus it and `0` takes the rest. Books of
    one criteria share one weight; weights sum to about BASE_WEIGHT_TOTAL.
    """
    path = gamestate.output_files.lookups[BASE_MODE]["paths"]["optimized_lookup"]
    criteria = read_criteria(gamestate, BASE_MODE)
    rows = read_lookup(path)

    p_trigger = trigger_probability(gamestate.config)
    p_hit = Fraction(str(PAR["base"]["hit_rate"]))
    odds = {"freegame": p_trigger, "basegame": p_hit - p_trigger, "0": 1 - p_hit}
    counts = {name: 0 for name in odds}
    for book_id, _, _ in rows:
        counts[criteria[book_id]] += 1
    if not all(counts.values()):
        raise RuntimeError(f"base needs books of every criteria, got {counts}")

    weights = {name: round(p * BASE_WEIGHT_TOTAL / counts[name]) for name, p in odds.items()}
    write_lookup(path, [(book_id, weights[criteria[book_id]], payout) for book_id, _, payout in rows])


def get_bet_mode(gamestate, mode: str):
    return next(bm for bm in gamestate.config.bet_modes if bm.get_name() == mode)


def read_lookup(path: str) -> list:
    with open(path, "r", encoding="UTF-8") as file:
        return [(int(r[0]), int(r[1]), int(r[2])) for r in csv.reader(file) if r]


def write_lookup(path: str, rows) -> None:
    with open(path, "w", encoding="UTF-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerows(rows)


def read_criteria(gamestate, mode: str) -> dict:
    with open(gamestate.output_files.lookups[mode]["paths"]["segmented_id"], "r", encoding="UTF-8") as file:
        return {int(r[0]): r[1] for r in csv.reader(file) if r}


def solve_tilt(rows, target: float, label: str) -> float:
    """theta such that the (weight, payout) rows reweighted by exp(theta * payout) have mean payout `target`."""
    by_payout = {}
    for _, weight, payout in rows:
        by_payout[payout] = by_payout.get(payout, 0) + weight
    payouts = list(by_payout)
    log_mass = [math.log(by_payout[p]) for p in payouts]
    if not min(payouts) < target < max(payouts):
        raise RuntimeError(f"{label}: target {target / 100}x outside book payouts {min(payouts) / 100}..{max(payouts) / 100}x")

    def mean_at(theta: float) -> float:
        exponents = [m + theta * p for m, p in zip(log_mass, payouts)]
        top = max(exponents)
        scaled = [math.exp(e - top) for e in exponents]
        return sum(s * p for s, p in zip(scaled, payouts)) / sum(scaled)

    low, high = -1e-6, 1e-6
    while mean_at(low) > target:
        low *= 2
    while mean_at(high) < target:
        high *= 2
    for _ in range(200):
        mid = (low + high) / 2
        if mean_at(mid) < target:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def tilted(rows, theta: float) -> list:
    """Rows reweighted by exp(theta * payout); equal-weight tables are scaled up first (TILT_MIN_WEIGHT)."""
    scale = max(1, math.ceil(TILT_MIN_WEIGHT / min(weight for _, weight, _ in rows)))
    return [(book_id, round(weight * scale * math.exp(theta * payout)), payout) for book_id, weight, payout in rows]


def tilt_weights(gamestate, mode: str) -> float:
    """Reweights a mode's lookup table onto its BetMode RTP with the smallest change in distribution.

    Every book's weight w becomes w * exp(theta * win) (exponential tilting: the minimum-KL
    reweighting with that mean), with theta solved so the weighted RTP equals the target.
    Hit rates and the shape of the win distribution stay close to the books' natural odds.
    Returns theta.
    """
    bet_mode = get_bet_mode(gamestate, mode)
    path = gamestate.output_files.lookups[mode]["paths"]["optimized_lookup"]
    rows = read_lookup(path)
    theta = solve_tilt(rows, bet_mode.get_rtp() * bet_mode.get_cost() * 100, mode)
    write_lookup(path, tilted(rows, theta))
    return theta


def clear_publish_lookups(gamestate, modes) -> None:
    """The SDK only writes `lookUpTable_<mode>_0.csv` when it is missing, so a rerun would keep the old table."""
    for mode in modes:
        path = gamestate.output_files.lookups[mode]["paths"]["optimized_lookup"]
        if os.path.exists(path):
            os.remove(path)


def vault_full_probability(config) -> Fraction:
    """Exact P(full grid) of the mwon vault round, from a Markov chain over (keys on the grid, respins left).

    Each respin every one of the `d` empty cells lands a key with p, so k keys land with
    C(d, k) p^k (1 - p)^(d - k); any key resets the respins, none uses one up.
    """
    settings = config.max_win_or_nothing
    cells = config.num_reels * config.num_rows[0]
    respins = settings["respins"]
    p = Fraction(str(settings["land_probability"]))
    states = {(settings["start_keys"], respins): Fraction(1)}
    full = Fraction(0)
    for keys in range(settings["start_keys"], cells):
        doors = cells - keys
        for left in range(respins, 0, -1):
            prob = states.pop((keys, left), 0)
            if not prob:
                continue
            for landed in range(doors + 1):
                q = prob * math.comb(doors, landed) * p**landed * (1 - p) ** (doors - landed)
                if keys + landed == cells:
                    full += q
                elif landed:
                    states[(keys + landed, respins)] = states.get((keys + landed, respins), 0) + q
                elif left > 1:
                    states[(keys, left - 1)] = states.get((keys, left - 1), 0) + q
    return full


def set_mwon_weights(gamestate) -> float:
    """Full-grid books share the exact P(full grid); the other books are tilted onto the published RTP.

    The other books (criteria `basegame`) are tilted so p * prize + (1 - p) * their mean equals
    the BetMode RTP x cost; the jackpot books (`wincap`) then split p / (1 - p) of that weight
    equally, so P(jackpot) is `vault_full_probability` up to integer rounding (< 1e-12).
    Returns theta of the tilt.
    """
    settings = gamestate.config.max_win_or_nothing
    bet_mode = get_bet_mode(gamestate, MWON_MODE)
    path = gamestate.output_files.lookups[MWON_MODE]["paths"]["optimized_lookup"]
    criteria = read_criteria(gamestate, MWON_MODE)
    rows = read_lookup(path)
    jackpots = [row for row in rows if criteria[row[0]] == "wincap"]
    others = [row for row in rows if criteria[row[0]] == "basegame"]
    prize = round(settings["win_amount"] * 100)
    if not jackpots or not others or len(jackpots) + len(others) != len(rows):
        raise RuntimeError(f"mwon needs only jackpot and other books, got {len(jackpots)} + {len(others)} of {len(rows)}")
    if any(payout != prize for _, _, payout in jackpots) or any(payout >= prize for _, _, payout in others):
        raise RuntimeError(f"only mwon jackpot books may pay {prize / 100}x")

    p = float(vault_full_probability(gamestate.config))
    target = (bet_mode.get_rtp() * bet_mode.get_cost() * 100 - p * prize) / (1 - p)
    theta = solve_tilt(others, target, f"{MWON_MODE} non-jackpot")
    others = tilted(others, theta)
    jackpot_weight = round(p / (1 - p) * sum(weight for _, weight, _ in others) / len(jackpots))
    weights = {book_id: weight for book_id, weight, _ in others}
    weights.update({book_id: jackpot_weight for book_id, _, _ in jackpots})
    write_lookup(path, [(book_id, weights[book_id], payout) for book_id, _, payout in rows])
    return theta


def main(num_sim_args=None, threads=NUM_THREADS, batching_size=BATCHING_SIZE, compression=COMPRESSION):
    num_sim_args = dict(num_sim_args or NUM_SIM_ARGS)
    # mwon is weighted by set_mwon_weights (exact jackpot share), never by the optimizer
    target_modes = [mode for mode in num_sim_args if mode != MWON_MODE]

    config = GameConfig()
    gamestate = GameState(config)

    if RUN_CONDITIONS["run_sims"]:
        clear_publish_lookups(gamestate, num_sim_args)
        create_books(gamestate, config, num_sim_args, batching_size, threads, compression, PROFILING)
        if BASE_MODE in num_sim_args:
            set_base_weights(gamestate)
        for mode in TILTED_MODES:
            if mode in num_sim_args:
                tilt_weights(gamestate, mode)
        if MWON_MODE in num_sim_args:
            set_mwon_weights(gamestate)

    generate_configs(gamestate)

    if RUN_CONDITIONS["run_optimization"]:
        from game_optimization import OptimizationSetup
        from optimization_program.run_script import OptimizationExecution

        OptimizationSetup(config)
        OptimizationExecution().run_all_modes(config, target_modes, RUST_THREADS)
        generate_configs(gamestate)

    if RUN_CONDITIONS["run_analysis"]:
        from game_optimization import OptimizationSetup
        from utils.game_analytics.run_analysis import create_stat_sheet

        OptimizationSetup(config)
        create_stat_sheet(gamestate, custom_keys=[{"symbol": "scatter"}])

    if RUN_CONDITIONS["run_format_checks"]:
        from utils.rgs_verification import execute_all_tests

        execute_all_tests(config)


if __name__ == "__main__":
    main()
