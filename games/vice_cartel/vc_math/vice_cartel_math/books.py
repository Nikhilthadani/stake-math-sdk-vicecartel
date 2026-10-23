"""Natural stratified lookup weights for Stake books (no optimizer).

Each outcome class c (plain spin by Wild count, five Wilds, each bonus tier, or a
whole buy mode) gets total weight equal to its EXACT natural probability. Inside
a class, books keep natural (equal) weight except for the minimum-chi-square
linear tilt  w_i = 1 + lam * (x_i - mean)  that moves the sample mean onto the
validated class mean. lam is of the order of one standard error, so the payout
distribution is not reshaped (unlike the old optimizer fences).
"""
from __future__ import annotations
import numpy as np

SCALE = 10 ** 9  # integer weight resolution per class


def tilt(payouts: np.ndarray, target_mean: float):
    x = np.asarray(payouts, float)
    m, v = x.mean(), x.var()
    if v == 0:
        if abs(m - target_mean) > 1e-12:
            raise ValueError("constant class cannot reach target")
        return np.ones_like(x), 0.0
    lam = (target_mean - m) / v
    w = 1.0 + lam * (x - m)
    if (w <= 0).any():
        raise ValueError(f"tilt too large (min weight {w.min():.3f}); generate more books for this class")
    return w, lam


def class_weights(classes: dict, exact_prob: dict, target_mean: dict, total=10 ** 15):
    """classes: {name: payouts array}. Returns {name: int weights}, report."""
    out, rep = {}, {}
    for c, x in classes.items():
        w, lam = tilt(x, target_mean[c])
        share = exact_prob[c] * total
        wi = np.maximum(1, np.rint(w / w.sum() * share)).astype(np.int64)
        out[c] = wi
        rep[c] = dict(n=len(x), sample_mean=float(np.mean(x)), target=target_mean[c],
                      lam=lam, max_weight_ratio=float(w.max() / w.min()),
                      deployed_mean=float((wi * x).sum() / wi.sum()))
    return out, rep


def deployed_rtp(weights: dict, classes: dict, cost: float) -> float:
    num = sum(float((weights[c] * classes[c]).sum()) for c in classes)
    den = sum(float(weights[c].sum()) for c in classes)
    return num / den / cost
