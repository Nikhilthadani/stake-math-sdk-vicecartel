"""
MWoN v2 (Sticky Wild Vault) - Monte Carlo of the actual hold & respin mechanic,
independent of the exact model in mwon_v2_model.py.

Usage: python3 mwon_v2_sim.py mwon_v2_analytic.json N SEED BATCHES [--out res.json]
"""
import json
import sys

import numpy as np


def play(rng, n, m):
    c = m["cfg"]
    C, R, p = c["cells"], c["respins"], m["p_land"]
    vals = np.array(c["mult_values"]); pr = np.array(m["mult_probs"])
    grid = np.zeros((n, C), bool)
    grid[:, : c["start_wilds"]] = True          # positions are cosmetic; start wilds in cells 0-4
    resp = np.full(n, R)
    respins_played = np.zeros(n, int)
    alive = np.ones(n, bool)
    while alive.any():
        idx = np.nonzero(alive)[0]
        land = (rng.random((len(idx), C)) < p) & ~grid[idx]
        grid[idx] |= land
        respins_played[idx] += 1
        new = land.any(axis=1)
        resp[idx] = np.where(new, R, resp[idx] - 1)
        full = grid[idx].all(axis=1)
        alive[idx] = (resp[idx] > 0) & ~full
    cnt = grid.sum(axis=1)
    mult = vals[rng.choice(len(vals), size=(n, C), p=pr)]
    s = (mult * grid).sum(axis=1)
    pay = np.where(cnt == C, c["jackpot"], np.minimum(c["cap"], np.maximum(c["floor"], s)))
    return pay.astype(float), cnt, respins_played


def main():
    a = sys.argv[1:]
    out = a[a.index("--out") + 1] if "--out" in a else None
    m = json.load(open(a[0])); n, seed, B = int(float(a[1])), int(a[2]), int(a[3])
    price = m["cfg"]["price"]
    batches, allp, allc, allr = [], [], [], []
    for b in range(B):
        pay, cnt, rp = play(np.random.default_rng([seed, b]), n, m)
        x = pay / price
        batches.append(dict(batch=b, seed=[seed, b], n=n, rtp=float(x.mean()), se=float(x.std(ddof=1) / np.sqrt(n)),
                            jackpots=int((cnt == 20).sum()), max=float(pay.max())))
        allp.append(pay); allc.append(cnt); allr.append(rp)
        print(f"batch {b}: RTP {x.mean():.4%} +/- {1.96 * batches[-1]['se']:.4%}  jackpots {batches[-1]['jackpots']}", flush=True)
    pay = np.concatenate(allp); cnt = np.concatenate(allc); rp = np.concatenate(allr)
    x = pay / price
    srt = np.sort(pay)[::-1]
    k = int(len(pay) * 0.001)
    res = dict(n=len(pay), rtp=float(x.mean()), se=float(x.std(ddof=1) / np.sqrt(len(x))),
               std_per_cost=float(x.std(ddof=1)), jackpot_rate=float((cnt == 20).mean()),
               nonjackpot_mean=float(pay[cnt < 20].mean()), p_floor=float((pay == m["cfg"]["floor"]).mean()),
               cvar_abs=float(srt[:k].mean()), max=float(pay.max()), min=float(pay.min()),
               mean_respins=float(rp.mean()), mean_wilds=float(cnt.mean()),
               count_dist={int(c): float((cnt == c).mean()) for c in np.unique(cnt)},
               pct=[float(np.percentile(pay, q)) for q in (10, 25, 50, 75, 90, 99, 99.9)],
               batches=batches)
    print(json.dumps({k: v for k, v in res.items() if k not in ("batches", "count_dist")}, indent=1))
    if out:
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
