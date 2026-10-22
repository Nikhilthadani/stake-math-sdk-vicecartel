"""
Max Win or Nothing v2 - "Sticky Wild Vault" (hold & respin). EXACT model + Stake-style checks.

Mechanic (PROVISIONAL parameters in CFG):
  * 20 cells. Round starts with N0=5 sticky wilds, each with a multiplier.
  * 3 respins. On each respin every EMPTY cell independently lands a wild with
    probability p (else blank). Any new wild resets respins to 3.
  * Ends when respins hit 0 or the grid is full.
  * Full grid (20 wilds)  -> 25,000x flat.
    Otherwise           -> min(cap, max(floor, sum of multipliers)).
  * Multipliers i.i.d. from MULT_VALUES with weights (same for start and new wilds).

Exact method: Markov chain over (wilds n, respins r) gives P(final n). For each
n < 20 the sum of n i.i.d. multipliers is an exact convolution. Together they
give the exact payout distribution, so every check below is exact.

Usage: python3 mwon_v2_model.py [--json out.json]
"""
import json
import sys

import numpy as np

CFG = dict(
    price=100, cells=20, start_wilds=5, respins=3, jackpot=25000, cap=2000, floor=20,
    mult_values=[1, 2, 3, 5, 10, 25, 50, 100],
    target_rtp=0.9635, target_jackpot_prob=1 / 1400,
)


def final_count_dist(p, cfg=CFG):
    """P(final number of wilds = n), n = start..cells (exact)."""
    C, R = cfg["cells"], cfg["respins"]
    from math import comb
    state = {(cfg["start_wilds"], R): 1.0}
    final = np.zeros(C + 1)
    while state:
        nxt = {}
        for (n, r), pr in state.items():
            e = C - n
            p0 = (1 - p) ** e
            # no new wild
            if r - 1 == 0:
                final[n] += pr * p0
            else:
                nxt[(n, r - 1)] = nxt.get((n, r - 1), 0) + pr * p0
            for k in range(1, e + 1):
                q = pr * comb(e, k) * p ** k * (1 - p) ** (e - k)
                if n + k == C:
                    final[C] += q
                else:
                    nxt[(n + k, R)] = nxt.get((n + k, R), 0) + q
        state = {k: v for k, v in nxt.items() if v > 1e-300}
    return final


def solve_p(cfg=CFG):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if final_count_dist(mid, cfg)[cfg["cells"]] < cfg["target_jackpot_prob"]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sum_dist(weights, n, values):
    """Exact distribution of the sum of n i.i.d. multipliers -> dict sum->prob."""
    w = np.array(weights, float) / sum(weights)
    vmax = max(values) * n
    base = np.zeros(max(values) + 1)
    for v, q in zip(values, w):
        base[v] += q
    d = np.zeros(1); d[0] = 1.0
    for _ in range(n):
        d = np.convolve(d, base)
    return d[: vmax + 1]


def payout_dist(p, weights, cfg=CFG):
    """Exact payout distribution: dict payout(x bet) -> prob."""
    fc = final_count_dist(p, cfg)
    out = {}
    for n in range(cfg["start_wilds"], cfg["cells"]):
        if fc[n] == 0:
            continue
        sd = sum_dist(weights, n, cfg["mult_values"])
        for s in np.nonzero(sd)[0]:
            pay = min(cfg["cap"], max(cfg["floor"], int(s)))
            out[pay] = out.get(pay, 0) + fc[n] * sd[s]
    out[cfg["jackpot"]] = out.get(cfg["jackpot"], 0) + fc[cfg["cells"]]
    return out, fc


def weights_family(t, values):
    """One-parameter weight family: w(v) = v^-t (scaled to integers later)."""
    return [v ** (-t) for v in values]


def rtp_of(p, weights, cfg=CFG):
    d, _ = payout_dist(p, weights, cfg)
    return sum(k * v for k, v in d.items()) / cfg["price"]


def solve_weights(p, cfg=CFG):
    lo, hi = 0.0, 4.0           # larger t -> lighter multipliers -> lower RTP
    for _ in range(80):
        mid = (lo + hi) / 2
        if rtp_of(p, weights_family(mid, cfg["mult_values"]), cfg) > cfg["target_rtp"]:
            lo = mid
        else:
            hi = mid
    return weights_family((lo + hi) / 2, cfg["mult_values"]), (lo + hi) / 2


def stake_checks(dist, cfg=CFG):
    """Checks as listed by the designer (definitions PROVISIONAL until confirmed in Stake docs)."""
    price = cfg["price"]
    xs = np.array(sorted(dist)); ps = np.array([dist[x] for x in xs])
    mean = (xs * ps).sum()
    rtp = mean / price
    std_cost = np.sqrt(((xs / price) ** 2 * ps).sum() - rtp ** 2)
    # CVaR: average payout of the worst (largest-payout) 0.1% of rounds
    tail, acc, q = 0.001, 0.0, 0.0
    for x, pr in zip(xs[::-1], ps[::-1]):
        take = min(pr, tail - q)
        acc += take * x
        q += take
        if q >= tail - 1e-15:
            break
    cvar = acc / tail
    rtp_share = lambda thr: (xs[xs > thr] * ps[xs > thr]).sum() / mean
    s40 = rtp_share(40 * price)
    s10k = rtp_share(10000)
    P = lambda thr: ps[xs >= thr].sum()
    res = dict(
        rtp=rtp, max_payout=float(xs.max()), cost=price, std_per_cost=std_cost,
        p_ge_5k=P(5000), p_ge_10k=P(10000), p_ge_25k=P(25000),
        cvar_abs=cvar, cvar_per_stake=cvar / price,
        share_gt_40x_cost=s40, share_gt_10k=s10k, share_both=s40 + s10k,
        share_both_x_cost=(s40 + s10k) * price,
        hit_rate=ps[xs > 0].sum(), hit_rate_1_in=1 / ps[xs > 0].sum(),
        mean_win=mean, nonjackpot_mean=(mean - cfg["jackpot"] * dist[cfg["jackpot"]]) / (1 - dist[cfg["jackpot"]]),
        p_floor=sum(v for k, v in dist.items() if k == cfg["floor"]),
        p_cap=dist.get(cfg["cap"], 0.0),
    )
    limits = {  # (2-star, 3-star) ; None = not specified for that tier -> use 2-star limit
        "max_payout": (50000, 100000), "cost": (1000, 5000), "std_per_cost": (50, 60),
        "p_ge_5k": (0.01, 0.01), "p_ge_10k": (0.005, 0.005), "p_ge_25k": (0.002, 0.002),
        "cvar_abs": (20000, 50000), "cvar_per_stake": (700, 700),
        "share_gt_40x_cost": (0.8, 0.9), "share_gt_10k": (0.6, 0.8), "share_both": (1.3, 1.5),
        "share_both_x_cost": (3000, 10000),
    }
    checks = []
    for k, (l2, l3) in limits.items():
        v = res[k]
        checks.append(dict(check=k, value=float(v), limit_2star=l2, limit_3star=l3,
                           pass_2star=bool(v <= l2), pass_3star=bool(v <= l3), headroom_2star=float(1 - v / l2)))
    checks.append(dict(check="hit_rate (>= 1 in 50)", value=float(res["hit_rate"]), limit_2star=0.02, limit_3star=0.02,
                       pass_2star=bool(res["hit_rate"] >= 0.02), pass_3star=bool(res["hit_rate"] >= 0.02),
                       headroom_2star=float(res["hit_rate"] / 0.02 - 1)))
    checks.append(dict(check="RTP within 96.0-96.7%", value=float(rtp), limit_2star=0.967, limit_3star=0.967,
                       pass_2star=bool(0.960 <= rtp <= 0.967), pass_3star=bool(0.960 <= rtp <= 0.967),
                       headroom_2star=float(min(rtp - 0.960, 0.967 - rtp))))
    return res, checks


def build(cfg=CFG):
    p = solve_p(cfg)
    w, t = solve_weights(p, cfg)
    # integer weights (book-friendly): scale so the 100x weight is ~1000, then re-tune RTP by
    # nudging the 1x weight (largest) so integer rounding does not move RTP.
    scale = 1000 / w[-1]
    wi = [int(round(x * scale)) for x in w]
    lo, hi = wi[0] // 2, wi[0] * 2
    for _ in range(60):
        mid = (lo + hi) // 2
        trial = [mid] + wi[1:]
        if rtp_of(p, trial, cfg) > cfg["target_rtp"]:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1:
            break
    cands = [[lo] + wi[1:], [hi] + wi[1:]]
    wi = min(cands, key=lambda c: abs(rtp_of(p, c, cfg) - cfg["target_rtp"]))
    dist, fc = payout_dist(p, wi, cfg)
    res, checks = stake_checks(dist, cfg)
    wn = np.array(wi) / sum(wi)
    return dict(cfg=cfg, p_land=p, weight_exponent=t, mult_weights=wi,
                mult_probs=wn.tolist(), mean_mult=float((np.array(cfg["mult_values"]) * wn).sum()),
                final_count_dist={int(n): float(fc[n]) for n in range(len(fc)) if fc[n] > 0},
                results={k: float(v) for k, v in res.items()}, checks=checks,
                payout_dist={int(k): float(v) for k, v in sorted(dist.items())})


if __name__ == "__main__":
    m = build()
    r = m["results"]
    print(f"p(land per empty cell per respin) = {m['p_land']:.6f}")
    print("multiplier weights:", dict(zip(m['cfg']['mult_values'], m['mult_weights'])), f"mean {m['mean_mult']:.3f}")
    print("final wild-count dist:", {k: round(v, 5) for k, v in m['final_count_dist'].items()})
    print(f"RTP {r['rtp']:.4%}  jackpot 1 in {1/m['final_count_dist'][20]:.1f}  non-jackpot mean {r['nonjackpot_mean']:.2f}x  "
          f"P(floor) {r['p_floor']:.3%}  P(cap) {r['p_cap']:.4%}")
    for c in m["checks"]:
        print(f"  {c['check']:24s} {c['value']:>12.6g}  2*:{'PASS' if c['pass_2star'] else 'FAIL'}  3*:{'PASS' if c['pass_3star'] else 'FAIL'}")
    if "--json" in sys.argv:
        json.dump(m, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
