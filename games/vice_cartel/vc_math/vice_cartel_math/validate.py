"""Full validation run. Writes reports/validation.json.

python -m vice_cartel_math.validate --tier 2000000 --base 20000000 --e2e 10000000 --m2w 10000000

Estimators
- Bonus tiers / buys: direct simulation of capped, floored rounds.
- Base / Extra Chance / buys (primary): exact pre-cap, pre-floor value plus
  the cap/floor correction simulated on paired paths (same draws played with
  and without the cap). Low variance; see tier_paired / base_precise.
- Base / Extra Chance (end-to-end): fully played rounds incl. bonuses. High
  variance, reported as an independent consistency check.
- Min 2 Wild: stratified by Wild count (exact P(K)), simulated E[pay | K].
- Golden Case: exact closed form + simulation.
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np
from . import config as C, sim as S, exact as X

TIERS = list(C.BONUS_TIERS)


def tiers(n, chunk=250_000):
    out = {}
    for i, tier in enumerate(TIERS):
        rng = np.random.default_rng(1000 + i)
        s1 = s2 = cnt = cap = mseg = 0.0; spins = 0; mxs = 0; zero = 0; mx = 0.0
        for _ in range(max(1, n // chunk)):
            st = {}
            w = S.floor_pay(S.run_bonus(rng, tier, np.zeros(chunk), st))
            s1 += w.sum(); s2 += (w * w).sum(); cnt += len(w); cap += (w >= C.WINCAP).sum()
            mseg += st["maxwin_segment"].sum(); spins += st["spins"].sum(); mxs = max(mxs, int(st["spins"].max()))
            zero += (w == 0).sum(); mx = max(mx, w.max())
        m = s1 / cnt; sd = np.sqrt(s2 / cnt - m * m)
        ex = X.bonus_ev(tier, detail=True)
        out[tier] = dict(N=int(cnt), ev=m, se=sd / np.sqrt(cnt), sd=sd, p_max_win=cap / cnt,
                         p_maxwin_segment=mseg / cnt, avg_spins=spins / cnt, max_spins=mxs,
                         p_zero=zero / cnt, max_observed=mx, exact_ev_uncapped=ex["ev"],
                         exact_p_maxwin_segment=ex["p_maxwin"], exact_avg_spins=ex["spins"])
        print(tier, {k: round(float(v), 5) for k, v in out[tier].items()}, flush=True)
    return out


def base_e2e(n, uplift, seed, chunk=1_000_000):
    rng = np.random.default_rng(seed)
    s1 = s2 = cnt = 0.0; caps = 0; mx = 0.0; bon = 0
    for _ in range(max(1, n // chunk)):
        v, d = S.play_base(rng, chunk, uplift, detail=True)
        s1 += v.sum(); s2 += (v * v).sum(); cnt += len(v); caps += (v >= C.WINCAP).sum()
        mx = max(mx, v.max()); bon += (d["scatters"] >= 3).sum()
    m = s1 / cnt; sd = np.sqrt(s2 / cnt - m * m)
    return dict(N=int(cnt), return_per_unit=m, se=sd / np.sqrt(cnt), sd_per_unit=sd,
                max_win_freq=caps / cnt, max_wins=int(caps), bonus_entries=int(bon), max_observed=mx)


def min2wild(n, seed=77, chunk=1_000_000):
    rng = np.random.default_rng(seed)
    _, pk = X.min2wild_ev()
    sums = np.zeros(6); sq = np.zeros(6); cnts = np.zeros(6); mx = 0.0; raw = []
    for _ in range(max(1, n // chunk)):
        v, k = S.play_min2wild(rng, chunk)
        raw.append(v.mean())
        for kk in range(2, 6):
            m = k == kk
            sums[kk] += v[m].sum(); sq[kk] += (v[m] ** 2).sum(); cnts[kk] += m.sum()
        mx = max(mx, v[k < 5].max())
    means = np.divide(sums, cnts, out=np.zeros(6), where=cnts > 0)
    var = np.divide(sq, cnts, out=np.zeros(6), where=cnts > 0) - means ** 2
    means[5] = C.WINCAP; var[5] = 0
    ev = float((pk * means).sum())
    se = float(np.sqrt(sum(pk[k] ** 2 * var[k] / cnts[k] for k in range(2, 5))))
    return dict(N=int(cnts.sum()), ev=ev, se=se, cost=C.BET_MODES["min2wild"]["cost"],
                rtp=ev / C.BET_MODES["min2wild"]["cost"], rtp_se=se / C.BET_MODES["min2wild"]["cost"],
                raw_mean=float(np.mean(raw)), exact_uncapped_ev=X.min2wild_ev()[0],
                p_k={k: float(pk[k]) for k in range(2, 6)}, max_win_freq=float(pk[5]),
                max_observed_below_5w=mx, mean_given_k={k: float(means[k]) for k in range(2, 6)})


def golden(n, seed=5):
    rng = np.random.default_rng(seed)
    v = S.play_golden(rng, n)
    rtp, p3 = X.golden_rtp()
    return dict(N=n, exact_rtp=rtp, exact_p_win=p3, sim_rtp=v.mean() / 1000,
                sim_se=v.std() / np.sqrt(n) / 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", type=int, default=2_000_000)
    ap.add_argument("--base", type=int, default=20_000_000)
    ap.add_argument("--e2e", type=int, default=10_000_000)
    ap.add_argument("--m2w", type=int, default=10_000_000)
    ap.add_argument("--paired", type=int, default=4_000_000)
    ap.add_argument("--out", default="reports/validation.json")
    a = ap.parse_args()
    t0 = time.time()
    rep = {"config": {"p_wild": C.PER_REEL_WILD_PROB, "trigger_total": C.SCATTER_TRIGGER_TOTAL,
                      "scatter_p": C.SCATTER_P_TRIGGER, "min2wild_q": C.MIN2WILD_EXTRA_PROB,
                      "wheel": {t: (v["wheel_prob"], v["maxwin_weight"]) for t, v in C.BONUS_TIERS.items()}}}
    rep["tiers"] = tiers(a.tier)
    rep["tiers_precise"] = tier_paired(a.paired)
    for mode, up, seed in (("base", 1.0, 21), ("extra_chance", C.EXTRA_CHANCE_UPLIFT, 22)):
        cost = C.BET_MODES[mode]["cost"]
        pr = base_precise(a.base, up, rep["tiers_precise"], seed + 10)
        pr["rtp"] = pr["return_per_unit"] / cost; pr["rtp_se"] = pr["se"] / cost
        e2e = base_e2e(a.e2e, up, seed + 100)
        e2e["rtp"] = e2e["return_per_unit"] / cost; e2e["rtp_se"] = e2e["se"] / cost
        ex, trig = X.base_components(up, {t: rep["tiers"][t]["exact_ev_uncapped"] for t in TIERS})
        rep[mode] = dict(cost=cost, precise=pr, end_to_end=e2e,
                         exact_prefloor_uncapped={k: float(v) / cost for k, v in ex.items()},
                         exact_trigger={t: float(v) for t, v in trig.items()})
        print(mode, "precise", pr["rtp"], pr["rtp_se"], "e2e", e2e["rtp"], e2e["rtp_se"], flush=True)
    for mode in ("bonus_normal", "bonus_super"):
        t = rep["tiers"][C.BET_MODES[mode]["tier"]]; cost = C.BET_MODES[mode]["cost"]
        tp = rep["tiers_precise"][C.BET_MODES[mode]["tier"]]
        rep[mode] = dict(cost=cost, rtp=t["ev"] / cost, rtp_se=t["se"] / cost, N=t["N"],
                         exact_uncapped_rtp=t["exact_ev_uncapped"] / cost,
                         precise=dict(rtp=tp["ev"] / cost, rtp_se=tp["se"] / cost, N=tp["N"]))
    rep["min2wild"] = min2wild(a.m2w)
    rep["golden_case"] = golden(20_000_000)
    rep["runtime_s"] = time.time() - t0
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(rep, open(a.out, "w"), default=float, indent=1)
    print("done", rep["runtime_s"])



# ------------------------------------------------------------------ precise
def tier_paired(n, chunk=250_000, seed0=5000):
    """EV(game) = exact EV(U) + E[floor(C) - U] on paired paths."""
    out = {}
    for i, tier in enumerate(TIERS):
        rng = np.random.default_rng(seed0 + i)
        s1 = s2 = cnt = 0.0; u1 = 0.0
        for _ in range(max(1, n // chunk)):
            Cg, U = S.run_bonus(rng, tier, np.zeros(chunk), paired=True)
            d = S.floor_pay(Cg) - U
            s1 += d.sum(); s2 += (d * d).sum(); cnt += len(d); u1 += U.sum()
        m = s1 / cnt; sd = np.sqrt(s2 / cnt - m * m)
        ex = X.bonus_ev(tier)
        out[tier] = dict(N=int(cnt), exact_uncapped=ex, correction=m, correction_se=sd / np.sqrt(cnt),
                         ev=ex + m, se=sd / np.sqrt(cnt), sim_U_mean=u1 / cnt)
        print("paired", tier, {k: round(float(v), 4) for k, v in out[tier].items()}, flush=True)
    return out


def base_precise(n, uplift, tier_prec, seed, chunk=1_000_000):
    """RTP = exact pre-floor/uncapped total (lines, scatter pay, five Wilds,
    exact P(tier) x exact tier EV) + simulated cap/floor correction of plain
    spins + exact P(tier) x tier correction."""
    ex, trig = X.base_components(uplift, {t: tier_prec[t]["exact_uncapped"] for t in TIERS})
    rng = np.random.default_rng(seed)
    s1 = s2 = cnt = 0.0
    for _ in range(max(1, n // chunk)):
        v, d = S.play_base(rng, chunk, uplift, detail=True, bonus_ev={t: 0.0 for t in TIERS})
        plain = (~d["five"]) & (d["scatters"] < 3)
        x = np.where(plain, v - d["spin_raw"], 0.0)
        s1 += x.sum(); s2 += (x * x).sum(); cnt += len(x)
    m = s1 / cnt; sd = np.sqrt(s2 / cnt - m * m)
    corr_t = sum(trig[t] * tier_prec[t]["correction"] for t in TIERS)
    se = np.sqrt((sd / np.sqrt(cnt)) ** 2 + sum((trig[t] * tier_prec[t]["se"]) ** 2 for t in TIERS))
    return dict(N=int(cnt), exact_uncapped_prefloor=ex["total"], plain_correction=m,
                tier_correction=corr_t, return_per_unit=ex["total"] + m + corr_t, se=float(se),
                bound_floor_interplay=0.1 * sum(trig.values()),
                contributions={k: float(v) for k, v in ex.items()})



if __name__ == "__main__":
    main()
