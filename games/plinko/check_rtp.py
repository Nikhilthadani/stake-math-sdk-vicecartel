"""RTP & sigma validation — reads lookup tables and compares simulated vs analytical.

Usage (from the SDK root):
    python games/plinko/check_rtp.py
"""

import os
import sys

SDK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, SDK_ROOT)
sys.path.insert(0, os.path.join(SDK_ROOT, "games", "plinko"))

from game_config import MODES, analytical_rtp, analytical_sigma, max_payout

LUT_DIR = os.path.join(SDK_ROOT, "games", "plinko", "library", "lookup_tables")
RTP_BAND = (0.960, 0.967)
MIN_SIGMA = 0.6


def read_lut_payout(filepath):
    """Return (weighted mean payout multiplier, row count) of a lookup table."""
    total_weight = total_payout = count = 0
    with open(filepath, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 3:
                weight, payout = int(parts[1]), int(parts[2])
                total_weight += weight
                total_payout += weight * payout
                count += 1
    if total_weight == 0:
        return 0, 0
    return total_payout / total_weight / 100.0, count


def flag(ok):
    return "Y" if ok else "N"


if __name__ == "__main__":
    print()
    print("=" * 74)
    print(f"  PLINKO VALIDATION  —  {len(MODES)} Modes")
    print("=" * 74)

    print("\n  ANALYTICAL (exact binomial, wheel included)")
    print("  {:<12} {:>5} {:>10} {:>8} {:>9} {:>7} {:>7}".format(
        "Mode", "Cost", "RTP", "sigma", "Max win", "RTP ok", "sig ok"))
    print("  " + "-" * 64)
    for name, spec in MODES.items():
        rtp = analytical_rtp(name)
        sigma = analytical_sigma(name)
        print("  {:<12} {:>5} {:>9.5f}% {:>8.4f} {:>9.2f} {:>7} {:>7}".format(
            name, spec["cost"], rtp * 100, sigma, max_payout(name),
            flag(RTP_BAND[0] <= rtp <= RTP_BAND[1]), flag(sigma >= MIN_SIGMA)))

    print("\n  SIMULATED vs ANALYTICAL (lookup tables)")
    print("  {:<12} {:>8} {:>10} {:>11} {:>10}  {}".format(
        "Mode", "Sims", "Sim RTP", "Analytical", "Delta", "Status"))
    print("  " + "-" * 64)

    deltas = []
    for name, spec in MODES.items():
        lut_path = os.path.join(LUT_DIR, f"lookUpTable_{name}.csv")
        if not os.path.exists(lut_path):
            print(f"  {name:<12}  FILE NOT FOUND")
            continue

        mean_payout, nsims = read_lut_payout(lut_path)
        sim_rtp = mean_payout / spec["cost"]
        ana_rtp = analytical_rtp(name)
        delta_pp = (sim_rtp - ana_rtp) * 100
        status = "OK" if abs(delta_pp) < 0.5 else ("~" if abs(delta_pp) < 1.5 else "HIGH")
        deltas.append((abs(delta_pp), status))
        print("  {:<12} {:>8} {:>9.4f}% {:>10.4f}% {:>+9.4f}pp  {}".format(
            name, nsims, sim_rtp * 100, ana_rtp * 100, delta_pp, status))

    if deltas:
        statuses = [s for _, s in deltas]
        print("  " + "-" * 64)
        print(f"  Max delta : {max(d for d, _ in deltas):.4f}pp")
        print(f"  Avg delta : {sum(d for d, _ in deltas) / len(deltas):.4f}pp")
        print(f"  Status    : {statuses.count('OK')} OK  |  {statuses.count('~')} warn  |  {statuses.count('HIGH')} high")

    print()
    print(f"  Target RTP: 96.10%  |  Stake band: {RTP_BAND[0]:.1%}-{RTP_BAND[1]:.1%}  |  Min sigma: {MIN_SIGMA}")
    print("=" * 74)
    print()
