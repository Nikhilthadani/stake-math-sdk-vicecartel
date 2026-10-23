"""Vice Cartel — natural stratified lookup weights (replaces the optimizer; vc_math CHANGE_REPORT §4).

Every book belongs to one class (its distribution criteria). A class's total weight is its exact natural
probability; inside a class the minimum-chi-square linear tilt (vc_math books.tilt) moves the sample mean
onto the class's exact mean, so the published RTP equals the validated RTP whatever the book count.

Class targets:
- plain spins / Min 2 Wild (no bonus): exact mean of the uncapped win (line EV per Wild set and Scatter
  count x exact mean multiplier of the class) plus the class's own cap/floor loss measured on its books;
- Scatter-triggered bonuses: exact trigger-spin EV + validated bonus EV (exact + paired cap/floor correction);
- bonus buys: validated bonus EV; five Wilds / Golden Case: fixed payouts.
"""

import csv
import glob
import itertools
import json
import os
from math import comb

import numpy as np

import game_config as G
from game_override import raw_wins_dir
from vc_math.vice_cartel_math import books as B, config as XC, exact as X

_VC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vc_math")
_VALIDATION = os.path.join(_VC_DIR, "reports", "validation.json")
WEIGHT_TOTAL = 10**18
MAX_WEIGHT_RATIO = 1.5  # in-class weights beyond this would visibly reshape the class
RTP_TOLERANCE = 0.0005
# min2wild keeps the vc_math q = 0.138188, whose exact paid RTP is 96.461%
RTP_TOLERANCE_BY_MODE = {"min2wild": 0.0007}


def _check_reference_matches_sdk() -> None:
    assert XC.PER_REEL_WILD_PROB == G.PER_REEL_WILD_PROB
    assert XC.MIN2WILD_EXTRA_PROB == G.MIN2WILD_EXTRA_PROB
    assert XC.EXTRA_CHANCE_UPLIFT == G.EXTRA_CHANCE_UPLIFT
    assert XC.GOLDEN_CASE_LETTER_PROB == G.GOLDEN_CASE_LETTER_PROB
    assert dict(zip(XC.WILD_MULTIPLIERS, XC.WILD_MULT_WEIGHTS)) == G.WILD_MULTIPLIER_WEIGHTS
    for n in (3, 4, 5, 6):
        assert abs(XC.SCATTER_P_TRIGGER[n] - G.SCATTER_COUNT_PROBS[n]) < 1e-15
    for tier, t in XC.BONUS_TIERS.items():
        assert (t["wheel_prob"], t["maxwin_weight"]) == (G.BONUS_TIERS[tier]["wheel_prob"], G.BONUS_TIERS[tier]["maxwin_weight"])


# ---------------------------------------------------------------- exact class values
def _mult_sum_pmf() -> dict[int, np.ndarray]:
    one = np.zeros(max(XC.WILD_MULTIPLIERS) + 1)
    one[list(XC.WILD_MULTIPLIERS)] = np.array(XC.WILD_MULT_WEIGHTS) / sum(XC.WILD_MULT_WEIGHTS)
    pmf = {0: np.array([1.0]), 1: one}
    for k in range(2, 6):
        pmf[k] = np.convolve(pmf[k - 1], one)
    return pmf


_PMF = _mult_sum_pmf()


def _mult_range_stats(k: int, lo: int, hi: int) -> tuple[float, float]:
    """(P(lo <= M <= hi), E[M | range]) for the sum M of k Wild multipliers."""
    s = np.arange(len(_PMF[k]))
    m = (s >= lo) & (s <= hi)
    p = float(_PMF[k][m].sum())
    return p, float((s[m] * _PMF[k][m]).sum() / p)


def _subsets(k: int):
    return list(itertools.combinations(range(5), k))


def _p_wild_count(k: int) -> float:
    p = XC.PER_REEL_WILD_PROB
    return comb(5, k) * p**k * (1 - p) ** (5 - k)


def _mean_lines(k: int, scatter_probs: dict[int, float]) -> float:
    """Mean 14-line win (multiplier 1) over Wild sets of size k, given a Scatter-count distribution."""
    tot = sum(scatter_probs.values())
    return float(np.mean([
        sum(p * 14 * X.ell(S, min(n, 4 * (5 - k))) for n, p in scatter_probs.items()) / tot
        for S in _subsets(k)
    ]))


def _validated_bonus_ev() -> dict[str, float]:
    with open(_VALIDATION, "r", encoding="UTF-8") as f:
        prec = json.load(f)["tiers_precise"]
    return {tier: prec[tier]["ev"] for tier in XC.BONUS_TIERS}


def base_class_specs(uplift: float, bonus_ev: dict[str, float]) -> dict[str, dict]:
    """{class: {prob, target | raw_mean}} for base / Extra Chance."""
    p5 = XC.PER_REEL_WILD_PROB ** 5
    sc = X.scatter_table(uplift)
    plain_sc = {n: sc[n] for n in (0, 1, 2)}
    p_plain = sum(plain_sc.values())
    specs = {"five_wilds": dict(prob=p5, target=XC.WINCAP)}
    for name in G.BASE_CLASS_BOOKS:
        if not name.startswith("plain_k"):
            continue
        cond = G.base_class_conditions(name)
        k = cond["wild_count"]
        p_range, mean_m = (1.0, 1.0) if k == 0 else _mult_range_stats(k, *cond["mult_range"])
        specs[name] = dict(prob=_p_wild_count(k) * p_range * p_plain,
                           raw_mean=_mean_lines(k, plain_sc) * mean_m)
    for n in (3, 4, 5, 6):
        target = 0.0
        for k in range(5):
            pk = _p_wild_count(k) / (1 - p5)
            n2 = min(n, 4 * (5 - k))
            mean_m = 1.0 if k == 0 else k * X.MU_W
            spin = _mean_lines(k, {n2: 1.0}) * mean_m + XC.SCATTER_PAY.get(n2, 0.0)
            target += pk * (spin + bonus_ev[XC.TIER_BY_SCATTERS[n2]])
        specs[f"bonus_sc{n}"] = dict(prob=(1 - p5) * sc[n], target=target)
    return specs


def min2wild_class_specs() -> dict[str, dict]:
    _, pk = X.min2wild_ev()
    specs = {"wilds5": dict(prob=float(pk[5]), target=XC.WINCAP)}
    for name in G.MIN2WILD_CLASS_BOOKS:
        if name == "wilds5":
            continue
        cond = G.min2wild_class_conditions(name)
        k = cond["wild_count"]
        p_range, mean_m = _mult_range_stats(k, *cond["mult_range"])
        specs[name] = dict(prob=float(pk[k]) * p_range, raw_mean=_mean_lines(k, {0: 1.0}) * mean_m)
    return specs


def mode_class_specs(mode: str) -> dict[str, dict]:
    bonus_ev = _validated_bonus_ev()
    if mode in ("base", "extra_chance"):
        return base_class_specs(1.0 if mode == "base" else XC.EXTRA_CHANCE_UPLIFT, bonus_ev)
    if mode == "min2wild":
        return min2wild_class_specs()
    if mode in G.BUY_BONUS_TIER:
        return {"freegame": dict(prob=1.0, target=bonus_ev[G.BUY_BONUS_TIER[mode]])}
    if mode == "golden_case":
        _, p3 = X.golden_rtp()
        return {"golden_win": dict(prob=p3, target=XC.WINCAP), "golden_lose": dict(prob=1 - p3, target=0.0)}
    raise ValueError(mode)


# ---------------------------------------------------------------- books in / weights out
def _read_mode_books(gamestate, mode: str):
    files = gamestate.output_files
    ids, payouts = [], []
    with open(files.get_final_lookup_name(mode), "r", encoding="UTF-8") as f:
        for book_id, _, payout in csv.reader(f):
            ids.append(int(book_id))
            payouts.append(int(payout))
    criteria = {}
    with open(files.get_final_segmented_name(mode), "r", encoding="UTF-8") as f:
        for row in csv.reader(f):
            criteria[int(row[0])] = row[1]
    raw = {}
    for path in glob.glob(os.path.join(raw_wins_dir(gamestate), f"raw_{mode}_*.csv")):
        with open(path, "r", encoding="UTF-8") as f:
            for book_id, value in csv.reader(f):
                raw[int(book_id)] = float(value)
    return np.array(ids), np.array(payouts), criteria, raw


def weight_mode(gamestate, mode: str) -> dict:
    """Compute and write publish_files/lookUpTable_<mode>_0.csv; return the per-class report."""
    cost = gamestate.get_betmode(mode).get_cost()
    specs = mode_class_specs(mode)
    ids, payout_ints, criteria, raw = _read_mode_books(gamestate, mode)
    paid = payout_ints / 100.0
    if mode == "golden_case":
        cls = np.where(payout_ints == int(XC.WINCAP * 100), "golden_win", "golden_lose")
    else:
        cls = np.array([criteria[i] for i in ids])

    classes, probs, targets, report = {}, {}, {}, {}
    for name, spec in specs.items():
        mask = cls == name
        assert mask.any(), f"{mode}: no books for class {name}"
        x = paid[mask]
        rep = dict(books=int(mask.sum()), prob=spec["prob"], sample_mean=float(x.mean()))
        if "raw_mean" in spec:
            r = np.array([raw[i] for i in ids[mask]])
            rep["raw_exact_mean"] = spec["raw_mean"]
            rep["raw_sample_mean"] = float(r.mean())
            rep["raw_z"] = float((r.mean() - spec["raw_mean"]) / (r.std() / np.sqrt(len(r)))) if r.std() > 0 else 0.0
            rep["cap_floor_correction"] = float((x - r).mean())
            target = spec["raw_mean"] + rep["cap_floor_correction"]
        else:
            target = spec["target"]
        classes[name], probs[name], targets[name] = x, spec["prob"], target
        rep["target"] = target
        report[name] = rep
    extra = set(np.unique(cls)) - set(specs)
    assert not extra, f"{mode}: books in unknown classes {extra}"
    assert abs(sum(probs.values()) - 1.0) < 1e-9, f"{mode}: class probabilities sum to {sum(probs.values())}"

    for name in classes:
        try:
            B.tilt(classes[name], targets[name])
        except ValueError as err:
            raise RuntimeError(f"{mode}/{name}: {err}") from err
    weights, tilt_rep = B.class_weights(classes, probs, targets, total=WEIGHT_TOTAL)
    for name, t in tilt_rep.items():
        report[name]["max_weight_ratio"] = t["max_weight_ratio"]
        report[name]["deployed_mean"] = t["deployed_mean"]

    by_id = {}
    for name in classes:
        for book_id, w in zip(ids[cls == name], weights[name]):
            by_id[int(book_id)] = int(w)
    out = gamestate.output_files.get_optimized_lookup_name(mode)
    with open(out, "w", encoding="UTF-8") as f:
        f.writelines(f"{i},{by_id[int(i)]},{p}\n" for i, p in zip(ids, payout_ints))

    w_all = np.array([by_id[int(i)] for i in ids], dtype=np.float64)
    deployed = float((w_all * paid).sum() / w_all.sum() / cost)
    expected = sum(probs[c] * targets[c] for c in classes) / cost
    return dict(mode=mode, cost=cost, deployed_rtp=deployed, expected_rtp=expected,
                total_weight=int(sum(by_id.values())), classes=report)


def apply_natural_weights(gamestate, modes) -> dict:
    """Weight every mode's books; raise if any mode misses its RTP or a class needs more books."""
    _check_reference_matches_sdk()
    results, problems = {}, []
    for mode in modes:
        res = weight_mode(gamestate, mode)
        results[mode] = res
        rtp_target = gamestate.get_betmode(mode).get_rtp()
        print(f"{mode:13s} deployed RTP {res['deployed_rtp']:.6%}  (class-exact {res['expected_rtp']:.6%}, "
              f"config {rtp_target:.2%}, books {sum(c['books'] for c in res['classes'].values()):,})")
        tol = RTP_TOLERANCE_BY_MODE.get(mode, RTP_TOLERANCE)
        if abs(res["deployed_rtp"] - rtp_target) > tol:
            problems.append(f"{mode}: deployed RTP {res['deployed_rtp']:.4%} is outside {rtp_target:.2%} +/- {tol:.2%}")
        for name, c in res["classes"].items():
            if c["max_weight_ratio"] > MAX_WEIGHT_RATIO:
                problems.append(f"{mode}/{name}: weight ratio {c['max_weight_ratio']:.3f}; generate more books")
            if abs(c.get("raw_z", 0.0)) > 4:
                problems.append(f"{mode}/{name}: uncapped win mean off its exact value (z={c['raw_z']:.2f})")
    report_path = os.path.join(gamestate.output_files.library_path, "weights_report.json")
    with open(report_path, "w", encoding="UTF-8") as f:
        json.dump(results, f, indent=1)
    if problems:
        raise RuntimeError("Natural weighting failed:\n  " + "\n  ".join(problems))
    return results
