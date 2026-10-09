"""RTP & sigma validation — reads lookup tables and compares simulated vs analytical."""

import os
from math import comb, sqrt

ROWS = [8, 10, 12, 14, 16]
RISKS = ["low", "medium", "high"]

# Must match game_config.py exactly
BASE_MULTIPLIERS = {
    8: {
        "low": [5.49, 2.13, 1.13, 1.11, 0.19, 1.11, 1.13, 2.13, 5.49],
        "medium": [12.63, 2.93, 1.25, 0.69, 0.38, 0.69, 1.25, 2.93, 12.63],
        "high": [28.09, 3.85, 1.46, 0.29, 0.2, 0.29, 1.46, 3.85, 28.09],
    },
    10: {
        "low": [8.67, 3.11, 1.47, 1.17, 1.11, 0.1, 1.11, 1.17, 1.47, 3.11, 8.67],
        "medium": [21.35, 4.84, 1.94, 1.36, 0.59, 0.38, 0.59, 1.36, 1.94, 4.84, 21.35],
        "high": [73.68, 9.69, 2.91, 0.87, 0.29, 0.2, 0.29, 0.87, 2.91, 9.69, 73.68],
    },
    12: {
        "low": [9.74, 2.76, 1.62, 1.62, 1.66, 0.75, 0.1, 0.75, 1.66, 1.62, 1.62, 2.76, 9.74],
        "medium": [32.02, 10.67, 3.9, 1.95, 1.07, 0.59, 0.27, 0.59, 1.07, 1.95, 3.9, 10.67, 32.02],
        "high": [164.82, 23.29, 7.83, 1.93, 0.67, 0.2, 0.2, 0.2, 0.67, 1.93, 7.83, 23.29, 164.82],
    },
    14: {
        "low": [6.89, 3.77, 1.87, 1.44, 1.52, 1.75, 0.64, 0.1, 0.64, 1.75, 1.52, 1.44, 1.87, 3.77, 6.89],
        "medium": [56.3, 14.56, 6.8, 3.88, 1.84, 0.97, 0.49, 0.19, 0.49, 0.97, 1.84, 3.88, 6.8, 14.56, 56.3],
        "high": [407.77, 54.39, 17.5, 4.84, 1.84, 0.29, 0.2, 0.19, 0.2, 0.29, 1.84, 4.84, 17.5, 54.39, 407.77],
    },
    16: {
        "low": [15.53, 6.55, 1.95, 1.39, 1.46, 1.37, 1.76, 0.61, 0.1, 0.61, 1.76, 1.37, 1.46, 1.39, 1.95, 6.55, 15.53],
        "medium": [106.79, 39.79, 9.69, 4.88, 2.9, 1.45, 0.97, 0.49, 0.29, 0.49, 0.97, 1.45, 2.9, 4.88, 9.69, 39.79, 106.79],
        "high": [970.95, 126.2, 25.25, 8.77, 3.87, 1.95, 0.2, 0.19, 0.19, 0.19, 0.2, 1.95, 3.87, 8.77, 25.25, 126.2, 970.95],
    },
}


def analytical_rtp(rows, mults):
    ev = sum(comb(rows, k) * mults[k] for k in range(rows + 1))
    return ev / (2 ** rows)


def analytical_sigma(rows, mults):
    probs = [comb(rows, k) / (2 ** rows) for k in range(rows + 1)]
    ex = sum(p * m for p, m in zip(probs, mults))
    ex2 = sum(p * m * m for p, m in zip(probs, mults))
    return sqrt(max(ex2 - ex * ex, 0))


def read_lut_rtp(filepath):
    total_weight = 0
    total_payout = 0
    count = 0
    with open(filepath, "r") as f:
        for line in f:
            parts = line.strip().split(",")
            if len(parts) == 3:
                weight = int(parts[1])
                payout_int = int(parts[2])
                total_weight += weight
                total_payout += weight * payout_int
                count += 1
    if total_weight == 0:
        return 0, 0
    return (total_payout / total_weight) / 100.0, count


if __name__ == "__main__":
    lut_dir = os.path.join("games", "plinko", "library", "lookup_tables")

    print()
    print("=" * 82)
    print("  PLINKO VALIDATION  —  15 Modes  (5 rows × 3 risks)")
    print("=" * 82)

    # Part 1: Analytical RTP + sigma
    print("\n  ANALYTICAL (exact binomial)")
    print("  {:<14} {:>10} {:>8} {:>8} {:>8}".format("Mode", "RTP", "sigma", "RTP ok", "sig ok"))
    print("  " + "-" * 52)

    for rows in ROWS:
        for risk in RISKS:
            mults = BASE_MULTIPLIERS[rows][risk]
            rtp = analytical_rtp(rows, mults)
            sigma = analytical_sigma(rows, mults)
            rtp_ok = "Y" if 0.960 <= rtp <= 0.967 else "N"
            sig_ok = "Y" if sigma >= 0.6 else "N"
            print("  {:<14} {:>9.5f}% {:>8.4f} {:>8} {:>8}".format(
                f"{rows}_{risk}", rtp * 100, sigma, rtp_ok, sig_ok))
        print()

    # Part 2: Simulated vs analytical (if lookup tables exist)
    print("  " + "=" * 74)
    print("  SIMULATED vs ANALYTICAL (lookup tables)")
    print("  " + "=" * 74)
    print()

    hdr = "  {:<14} {:>7} {:>10} {:>12} {:>10}  {}".format(
        "Mode", "Sims", "Sim RTP", "Analytical", "Delta", "Status")
    print(hdr)
    print("  " + "-" * 70)

    max_delta = 0
    results = []

    for rows in ROWS:
        for risk in RISKS:
            name = f"{rows}_{risk}"
            lut_path = os.path.join(lut_dir, f"lookUpTable_{name}.csv")

            if not os.path.exists(lut_path):
                print(f"  {name:<14}  FILE NOT FOUND")
                continue

            sim_rtp, nsims = read_lut_rtp(lut_path)
            ana_rtp = analytical_rtp(rows, BASE_MULTIPLIERS[rows][risk])
            delta = sim_rtp - ana_rtp
            delta_pp = abs(delta) * 100
            max_delta = max(max_delta, delta_pp)

            status = "OK" if delta_pp < 0.5 else ("~" if delta_pp < 1.5 else "HIGH")
            sign = "+" if delta >= 0 else "-"
            print("  {:<14} {:>7} {:>9.4f}% {:>10.4f}%  {}{:>7.4f}pp  {}".format(
                name, nsims, sim_rtp * 100, ana_rtp * 100, sign, delta_pp, status))
            results.append((name, sim_rtp, ana_rtp, delta_pp, status))

        if rows < 16:
            print("  " + "." * 70)

    if results:
        print()
        print("  " + "=" * 70)
        avg_delta = sum(r[3] for r in results) / len(results)
        ok_count = sum(1 for r in results if r[4] == "OK")
        warn_count = sum(1 for r in results if r[4] == "~")
        high_count = sum(1 for r in results if r[4] == "HIGH")
        print(f"  Max delta         : {max_delta:.4f}pp")
        print(f"  Avg delta         : {avg_delta:.4f}pp")
        print(f"  Status            : {ok_count} OK  |  {warn_count} warn  |  {high_count} high")
    print()
    print("  Target RTP: ~96.10%  |  Stake band: 96.0-96.7%  |  Min sigma: 0.6")
    print("  " + "=" * 70)
    print()
