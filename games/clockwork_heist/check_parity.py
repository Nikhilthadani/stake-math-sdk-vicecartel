"""Parity check of the Stake port against the engine-clockwork PAR sheet.

Plays natural rounds (no criteria forcing, no redraws, equal weights) through the
real `GameState.run_spin` and reports the same metrics as
`engine-clockwork/scripts/rtp/simulate.ts`, compared with `Slot_Game_PAR_Sheet.xlsx`.

    python games/clockwork_heist/check_parity.py                       # 10M base, 1M bonus, 1M mwon
    python games/clockwork_heist/check_parity.py --modes bonus --rounds 100000 --workers 8

A metric passes when it is inside the 95% confidence interval of the PAR value
(|z| <= 1.96). RTP against the 96.0-96.7% target band is reported, not enforced:
run.py's lookup weights set the published RTP.
"""

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

GAME_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GAME_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(GAME_DIR, "..", "..")))

from game_config import GameConfig  # noqa: E402
from gamestate import GameState  # noqa: E402
from memory_guard import DEFAULT_LIMIT, MemoryWatchdog, workers_within_budget  # noqa: E402
from src.events.events import reveal_event  # noqa: E402

# Peak working set of one worker (config, reels, one round of events), measured ~180 MB, with margin
WORKER_BYTES = 300 * 2**20

DEFAULT_ROUNDS = {"base": 10_000_000, "bonus": 1_000_000, "mwon": 1_000_000}
CRITERIA = {"base": "basegame", "bonus": "freegame", "mwon": "basegame"}
TARGET_RTP = (0.96, 0.967)
Z_LIMIT = 1.96
MAX_SPINS = 14

# E[win on free spin i | played], 8-spin session ("FS Analysis", Markov chain)
FS_SPIN_MEAN = [0.629324630047967, 1.55015917083783, 2.91508561095015, 4.74291258456104, 7.0411743665272,
                9.80821856512111, 13.0349946184511, 16.7065814533904, 55.8825723166297, 62.9337653184534,
                70.1439360297512, 263.71115833326, 269.234007208467, 274.580814820179]

# Slot_Game_PAR_Sheet.xlsx: "Simulation" (theoretical column), "FS Analysis" (Markov chain).
# mwon: mathsV2/Slot_Game_PAR_Sheet_V2.xlsx "MWoN v2", exact (mwon_v2_model.py) at land probability 0.049132085.
PAR = {
    "base": {"rtp": 0.960293368120705, "line_rtp": 0.53572422485447, "fs_rtp": 0.424569143266236,
             "trigger_interval": 226.295577808039, "hit_rate": 0.336594775},
    "bonus": {"rtp": 0.960781195948969},
    "mwon": {"rtp": 0.963506278196, "jackpot_rate": 0.000714285755690687, "non_jackpot_mean": 78.5495907811,
             "min_award_rate": 0.114300455085, "keys": 10.1933468886},
    "session": {
        "mean": 96.0781195948969, "raw_mean": 93.1167756198969, "spins": 8.57628442870623,
        "keys": 3.34551741886352, "min_award_rate": 0.39386775,
        "awards": [0.808535740799767, 0.190833708831722, 0.00063055036851099],
        "spin_mean": FS_SPIN_MEAN,
    },
}
# Rounds behind PAR values that are simulation results, not closed-form ("Simulation" sheet)
PAR_SIM_ROUNDS = {"base": 40_000_000, "bonus": 4_000_000}


class NaturalGameState(GameState):
    """Plays rounds as the engine does: boards are never forced or redrawn and every round is kept."""

    def draw_board(self, emit_event: bool = True, trigger_symbol: str = "scatter") -> None:
        self.create_board_reelstrips()
        if emit_event:
            reveal_event(self)

    def check_freespin_entry(self, scatter_key: str = "scatter") -> bool:
        return True

    def check_repeat(self) -> None:
        self.repeat = False

    def imprint_wins(self) -> None:
        """Books are not written here; the SDK version keeps every finished book in memory."""
        self.temp_wins = []
        self.win_manager.update_end_round_wins()


def empty_stats() -> dict:
    return {
        "rounds": 0, "win": 0.0, "paid_win": 0.0, "win_sq": 0.0, "hits": 0, "max_win": 0.0, "capped": 0, "base_win": 0.0,
        "sessions": 0, "session_win": 0.0, "session_sq": 0.0, "raw_win": 0.0, "spins": 0, "keys": 0,
        "min_award": 0, "awards": [0, 0, 0], "spin_win": [0.0] * MAX_SPINS, "spin_played": [0] * MAX_SPINS,
        "vault_full": 0, "vault_other_win": 0.0, "vault_other_sq": 0.0, "vault_min_award": 0, "vault_keys": 0,
        "vault_keys_sq": 0, "vault_bad": 0,
    }


def run_chunk(job: tuple) -> dict:
    mode, first_sim, rounds, seed = job
    gs = NaturalGameState(GameConfig())
    gs.betmode = mode
    gs.criteria = CRITERIA[mode]
    vault = gs.config.max_win_or_nothing
    cells = gs.config.num_reels * gs.config.num_rows[0]
    initial_spins = gs.config.free_spins["initial_spins"]
    s = empty_stats()

    for sim in range(first_sim, first_sim + rounds):
        gs.run_spin(sim + seed * 100_000_000)

        win = gs.exact_win
        s["rounds"] += 1
        s["win"] += win
        s["paid_win"] += gs.final_win
        s["win_sq"] += win * win
        s["hits"] += win > 0
        s["max_win"] = max(s["max_win"], win)
        s["capped"] += gs.wincap_triggered

        fs = gs.fs_summary
        if mode == "mwon":
            v = gs.vault_summary
            keys = v["keys"]
            expected = vault["win_amount"] if v["full"] else max(v["multiplier_sum"], vault["min_award"])
            s["vault_bad"] += not (fs is None and win == expected and v["full"] == (keys == cells)
                                   and keys == len(gs.vault) and v["multiplier_sum"] == sum(gs.vault.values()))
            s["vault_keys"] += keys
            s["vault_keys_sq"] += keys * keys
            s["vault_min_award"] += v["min_award_applied"]
            if v["full"]:
                s["vault_full"] += 1
            else:
                s["vault_other_win"] += win
                s["vault_other_sq"] += win * win
            continue
        s["base_win"] += gs.win_manager.basegame_wins
        if fs is None:
            continue
        s["sessions"] += 1
        session = gs.win_manager.freegame_wins
        s["session_win"] += session
        s["session_sq"] += session * session
        s["raw_win"] += fs["raw_win"]
        s["spins"] += fs["spins"]
        s["keys"] += fs["keys"]
        s["min_award"] += fs["top_up"] > 0
        s["awards"][(fs["spins"] - initial_spins) // gs.config.free_spins["spins_per_award"]] += 1
        for i, spin_win in enumerate(fs["spin_wins"]):
            s["spin_win"][i] += spin_win
            s["spin_played"][i] += 1
    return s


def merge(parts: list) -> dict:
    total = empty_stats()
    for part in parts:
        for key, value in part.items():
            if key == "max_win":
                total[key] = max(total[key], value)
            elif isinstance(value, list):
                total[key] = [a + b for a, b in zip(total[key], value)]
            else:
                total[key] += value
    return total


def metric(name: str, sim: float, par: float, se: float = None) -> dict:
    row = {"metric": name, "sim": sim, "par": par}
    if se:
        row["se"] = se
        row["z"] = (sim - par) / se
        row["pass"] = abs(row["z"]) <= Z_LIMIT
    return row


def proportion_se(p: float, n: int, par_n: int = None) -> float:
    """SE of a simulated proportion; `par_n` adds the noise of a PAR value that is itself simulated."""
    variance = p * (1 - p) / n if n else 0.0
    if par_n:
        variance += p * (1 - p) / par_n
    return math.sqrt(max(variance, 0))


def summarize(mode: str, s: dict, cost: float) -> list:
    n = s["rounds"]
    mean = s["win"] / n
    rtp_se = math.sqrt(max(s["win_sq"] / n - mean * mean, 0) / n) / cost
    rows = [metric("RTP", mean / cost, PAR[mode]["rtp"], rtp_se)]
    sessions = s["sessions"]
    if mode == "mwon":
        par = PAR["mwon"]
        others = n - s["vault_full"]
        other_mean = s["vault_other_win"] / others
        other_se = math.sqrt(max(s["vault_other_sq"] / others - other_mean ** 2, 0) / others)
        keys_mean = s["vault_keys"] / n
        keys_se = math.sqrt(max(s["vault_keys_sq"] / n - keys_mean ** 2, 0) / n)
        rows += [
            metric("jackpot rate (full grid)", s["vault_full"] / n, par["jackpot_rate"], proportion_se(par["jackpot_rate"], n)),
            metric("non-jackpot mean (x bet)", other_mean, par["non_jackpot_mean"], other_se),
            metric("P(20x minimum paid)", s["vault_min_award"] / n, par["min_award_rate"], proportion_se(par["min_award_rate"], n)),
            metric("keys on the final grid", keys_mean, par["keys"], keys_se),
            metric("rounds breaking the rules", s["vault_bad"], 0),
        ]
        return rows
    if mode == "base":
        hit_par = PAR["base"]["hit_rate"]
        trigger_p = 1 / PAR["base"]["trigger_interval"]
        rows += [
            metric("hit rate", s["hits"] / n, hit_par, proportion_se(hit_par, n, PAR_SIM_ROUNDS["base"])),
            metric("line RTP", s["base_win"] / n, PAR["base"]["line_rtp"]),
            metric("free spins RTP", (s["win"] - s["base_win"]) / n, PAR["base"]["fs_rtp"]),
            metric("trigger rate", sessions / n, trigger_p, proportion_se(trigger_p, n)),
        ]
    if not sessions:
        return rows

    sp = PAR["session"]
    par_rounds = PAR_SIM_ROUNDS["bonus"]
    session_mean = s["session_win"] / sessions
    session_sd = math.sqrt(max(s["session_sq"] / sessions - session_mean ** 2, 0))
    session_se = session_sd / math.sqrt(sessions)
    min_rate = s["min_award"] / sessions
    rows += [
        metric("session mean (x bet)", session_mean, sp["mean"], session_se),
        metric("raw session mean (x bet)", s["raw_win"] / sessions, sp["raw_mean"], session_se),
        metric("spins per session", s["spins"] / sessions, sp["spins"]),
    ]
    if "keys" in sp:
        rows.append(metric("keys per session", s["keys"] / sessions, sp["keys"]))
    rows.append(metric("P(10x minimum paid)", min_rate, sp["min_award_rate"],
                       proportion_se(sp["min_award_rate"], sessions, par_rounds)))
    for k, p in enumerate(sp.get("awards", [])):
        rows.append(metric(f"P({k} Gold Meter awards)", s["awards"][k] / sessions, p, proportion_se(p, sessions)))
    for i, par_mean in enumerate(sp["spin_mean"]):
        if s["spin_played"][i]:
            rows.append(metric(f"E[win | spin {i + 1} played]", s["spin_win"][i] / s["spin_played"][i], par_mean))
    return rows


def format_mode(mode: str, s: dict, cost: float, rows: list, seconds: float) -> str:
    rtp, se = rows[0]["sim"], rows[0].get("se", 0.0)
    published = "published RTP is set by the lookup weights"
    band = "in band" if TARGET_RTP[0] <= rtp <= TARGET_RTP[1] else "outside band"
    lines = [
        f"== {mode}  ({s['rounds']:,} rounds, cost {cost:g}x, {seconds:.0f}s)",
        f"  natural RTP {rtp * 100:.3f}% +/- {1.96 * se * 100:.3f}%   "
        f"target {TARGET_RTP[0] * 100:.1f}-{TARGET_RTP[1] * 100:.1f}%: {band} ({published})",
        f"  paid RTP (Stake, wins rounded down to 0.1x) {s['paid_win'] / s['rounds'] / cost * 100:.3f}%",
        f"  max win {s['max_win']:,.2f}x   rounds at max win {s['capped']:,}"
        + (f"   sessions {s['sessions']:,}" if s["sessions"] else ""),
        f"  {'metric':<32}{'port':>14}{'PAR':>14}{'z':>8}",
    ]
    for row in rows:
        z = f"{row['z']:+.2f}" if "z" in row else ""
        status = "" if "pass" not in row else ("  ok" if row["pass"] else "  FAIL")
        lines.append(f"  {row['metric']:<32}{row['sim']:>14.6f}{row['par']:>14.6f}{z:>8}{status}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modes", default="base,bonus,mwon", help="comma list of base, bonus, mwon")
    parser.add_argument("--rounds", type=int, help="rounds per mode (default: 10M base, 1M bonus, 1M mwon)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    parser.add_argument("--seed", type=int, default=1, help="seed set; each value gives independent rounds")
    parser.add_argument("--memory-limit", type=float, default=DEFAULT_LIMIT,
                        help="max share of system RAM in use (default 0.80); the run stops past it")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for mode in modes:
        if mode not in DEFAULT_ROUNDS:
            parser.error(f"unknown mode: {mode}")

    workers = workers_within_budget(args.workers, WORKER_BYTES, args.memory_limit)
    if workers < args.workers:
        print(f"Using {workers} workers (not {args.workers}) to stay under {args.memory_limit:.0%} RAM", flush=True)
    args.workers = workers

    config = GameConfig()
    costs = {bm.get_name(): bm.get_cost() for bm in config.bet_modes}
    report, text, failures = {"seed": args.seed, "workers": args.workers, "modes": {}}, [], 0

    for mode in modes:
        rounds = args.rounds or DEFAULT_ROUNDS[mode]
        per_worker = -(-rounds // args.workers)
        jobs = [(mode, w * per_worker, min(per_worker, rounds - w * per_worker), args.seed)
                for w in range(args.workers) if w * per_worker < rounds]
        started = time.time()
        with MemoryWatchdog(args.memory_limit) as watchdog, Pool(len(jobs)) as pool:
            stats = merge(pool.map(run_chunk, jobs))
        seconds = time.time() - started
        print(f"  peak system memory {watchdog.peak:.0%}", flush=True)

        rows = summarize(mode, stats, costs[mode])
        failures += sum(1 for row in rows if row.get("pass") is False)
        if mode == "mwon":
            failures += stats["vault_bad"] > 0
        block = format_mode(mode, stats, costs[mode], rows, seconds)
        print(block + "\n", flush=True)
        text.append(block)
        report["modes"][mode] = {"rounds": stats["rounds"], "seconds": seconds, "max_win": stats["max_win"],
                                 "capped": stats["capped"], "metrics": rows}

    out_dir = os.path.join(GAME_DIR, "library", "parity")
    os.makedirs(out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    with open(os.path.join(out_dir, f"parity_{stamp}.json"), "w", encoding="UTF-8") as file:
        json.dump(report, file, indent=2)
    with open(os.path.join(out_dir, f"parity_{stamp}.txt"), "w", encoding="UTF-8") as file:
        file.write("\n\n".join(text) + "\n")

    print(f"{'PASS' if not failures else f'FAIL ({failures} checks outside 95% CI)'}"
          f"   report: library/parity/parity_{stamp}.txt")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
