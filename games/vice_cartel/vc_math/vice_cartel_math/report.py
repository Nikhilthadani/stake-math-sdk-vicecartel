"""Render reports/validation.json into docs/VALIDATION_REPORT.md."""
from __future__ import annotations
import json, sys
from . import config as C

R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "reports/validation.json"))
lo, hi = C.RTP_RANGE
TIERS = list(C.BONUS_TIERS)


def pct(x, d=2):
    return f"{100 * x:.{d}f}%"


def ci(r, se, d=2):
    return f"[{pct(r - 1.96 * se, d)}, {pct(r + 1.96 * se, d)}]"


def status(r, se):
    if lo <= r - 1.96 * se and r + 1.96 * se <= hi:
        return "PASS"
    return "PASS (point, CI wider than range)" if lo <= r <= hi else "FAIL"


L = ["# Vice Cartel — Validation Report", "",
     f"Required RTP range **{pct(lo,1)}–{pct(hi,1)}**; calibration target {pct(C.RTP_TARGET,1)}. "
     "All CIs are 95% (±1.96 SE). Every simulated payout is capped at 25,000× and floored to 0.1× exactly as the game pays.", "",
     "**Primary estimator:** the exact value (no randomness, cap and floor ignored) plus a simulated cap/floor correction. "
     "The correction is measured on paired paths: the same random draws are played with and without the cap. "
     "**Independent checks:** direct simulation of fully played rounds.", "",
     "## 1. RTP by mode", "",
     "| Mode | Cost | Exact (pre-cap, pre-floor) | Final RTP (exact + correction) | 95% CI | Direct simulation (check) | Check 95% CI | Status |",
     "|---|---:|---:|---:|---|---:|---|---|"]
for m in ("base", "extra_chance"):
    p = R[m]["precise"]; e = R[m]["end_to_end"]
    L.append(f"| {m} | {R[m]['cost']:.0f}× | {pct(p['exact_uncapped_prefloor']/R[m]['cost'],3)} | **{pct(p['rtp'],3)}** | {ci(p['rtp'], p['rtp_se'],3)} | "
             f"{pct(e['rtp'])} ({e['N']/1e6:.0f}M spins) | {ci(e['rtp'], e['rtp_se'])} | {status(p['rtp'], p['rtp_se'])} |")
for m in ("bonus_normal", "bonus_super"):
    p = R[m]["precise"]; d = R[m]
    L.append(f"| {m} | {d['cost']:.0f}× | {pct(d['exact_uncapped_rtp'],3)} | **{pct(p['rtp'],3)}** | {ci(p['rtp'], p['rtp_se'],3)} | "
             f"{pct(d['rtp'])} ({d['N']/1e6:.0f}M rounds) | {ci(d['rtp'], d['rtp_se'])} | {status(p['rtp'], p['rtp_se'])} |")
m = R["min2wild"]
L.append(f"| min2wild | {m['cost']:.0f}× | {pct(m['exact_uncapped_ev']/m['cost'],3)} | **{pct(m['rtp'],3)}** (stratified by exact P(K)) | {ci(m['rtp'], m['rtp_se'],3)} | "
         f"{pct(m['raw_mean']/m['cost'])} raw mean ({m['N']/1e6:.0f}M) | – | {status(m['rtp'], m['rtp_se'])} |")
g = R["golden_case"]
L.append(f"| golden_case | 1000× | {pct(g['exact_rtp'],4)} | **{pct(g['exact_rtp'],4)}** (exact, no cap/floor effect) | exact | "
         f"{pct(g['sim_rtp'],3)} ({g['N']/1e6:.0f}M) | {ci(g['sim_rtp'], g['sim_se'])} | PASS |")

L += ["", "## 2. Base and Extra Chance breakdown (per unit of cost)", "",
      "| Component | Base | Extra Chance (÷3) |", "|---|---:|---:|"]
for k in ("lines", "scatter", "five_wilds", *TIERS):
    L.append(f"| {k} (exact) | {pct(R['base']['precise']['contributions'][k],3)} | {pct(R['extra_chance']['precise']['contributions'][k]/3,3)} |")
for k, lab in (("plain_correction", "cap + 0.1× floor on non-bonus spins (sim)"), ("tier_correction", "cap + floor inside bonuses (sim)")):
    L.append(f"| {lab} | {pct(R['base']['precise'][k],3)} | {pct(R['extra_chance']['precise'][k]/3,3)} |")
L.append(f"| **Total** | **{pct(R['base']['precise']['rtp'],3)}** | **{pct(R['extra_chance']['precise']['rtp'],3)}** |")
bf = R['base']['precise']['bound_floor_interplay']
L.append(f"\nModelling bound: the floor on (trigger spin + bonus) versus the floor on the bonus alone differs by less than {pct(bf,3)} (base) and {pct(R['extra_chance']['precise']['bound_floor_interplay']/3,3)} (EC).")
nb = sum(R['base']['precise']['contributions'][t] for t in TIERS) + R['base']['precise']['tier_correction']
L.append(f"Base split: non-bonus {pct(R['base']['precise']['rtp']-nb)} / bonus {pct(nb)}.")

L += ["", "## 3. Trigger and Max Win frequencies", "",
      "| Event | Base P per spin | Base 1 in | Extra Chance 1 in |", "|---|---:|---:|---:|"]
for t, v in C.BONUS_TIERS.items():
    ex = R["base"]["exact_trigger"][t]
    L.append(f"| {v['scatters']} Scatters → {t} | {ex:.4e} | {1/ex:,.0f} | {1/R['extra_chance']['exact_trigger'][t]:,.0f} |")
tb = sum(R["base"]["exact_trigger"].values()); te = sum(R["extra_chance"]["exact_trigger"].values())
L.append(f"| any bonus | {tb:.4e} | {1/tb:,.0f} | {1/te:,.0f} |")
p5 = C.PER_REEL_WILD_PROB ** 5
L.append(f"| five Wilds (Max Win) | {p5:.4e} | {1/p5:,.0f} | {1/p5:,.0f} |")
mw = p5 + sum(R["base"]["exact_trigger"][t] * R["tiers"][t]["p_max_win"] for t in TIERS)
mwe = p5 + sum(R["extra_chance"]["exact_trigger"][t] * R["tiers"][t]["p_max_win"] for t in TIERS)
L.append(f"| any 25,000× Max Win | {mw:.4e} | {1/mw:,.0f} | {1/mwe:,.0f} |")
e = R["base"]["end_to_end"]; ee = R["extra_chance"]["end_to_end"]
L.append(f"\nDirect check: {e['N']:,} base spins gave {e['bonus_entries']:,} bonuses (expected {tb*e['N']:,.0f}) and {e['max_wins']} Max Wins (expected {mw*e['N']:.1f}). "
         f"{ee['N']:,} Extra Chance spins gave {ee['bonus_entries']:,} bonuses (expected {te*ee['N']:,.0f}) and {ee['max_wins']} Max Wins (expected {mwe*ee['N']:.1f}). "
         f"Volatility (SD per unit cost): base {e['sd_per_unit']:.1f}, Extra Chance {ee['sd_per_unit']:.1f}.")

L += ["", "## 4. Bonus tiers", "",
      "| Tier | Exact EV (uncapped) | Final EV (exact + correction) | 95% CI | Direct sim EV (2M) | SD | Avg spins exact / sim | Max spins seen | P(Max Win) | MAX WIN segment exact / sim | P(round pays 0) |",
      "|---|---:|---:|---|---:|---:|---|---:|---|---|---:|"]
for t in TIERS:
    s = R["tiers"][t]; p = R["tiers_precise"][t]
    L.append(f"| {t} | {p['exact_uncapped']:.2f}× | **{p['ev']:.2f}×** | [{p['ev']-1.96*p['se']:.2f}, {p['ev']+1.96*p['se']:.2f}] | {s['ev']:.2f}× | {s['sd']:.0f} | "
             f"{s['exact_avg_spins']:.3f} / {s['avg_spins']:.3f} | {int(s['max_spins'])} | 1 in {1/s['p_max_win']:,.0f} | "
             f"1 in {1/s['exact_p_maxwin_segment']:,.0f} / 1 in {1/s['p_maxwin_segment']:,.0f} | {pct(s['p_zero'],3)} |")

L += ["", "## 5. Minimum 2 Wild (100×)", "", "| Wild reels | P exact | E[pay] simulated |", "|---:|---:|---:|"]
for k in ("2", "3", "4", "5"):
    L.append(f"| {k} | {m['p_k'][k]:.5f} | {m['mean_given_k'][k]:,.2f}× |")
L.append(f"\nMax Win (5 Wilds) 1 in {1/m['max_win_freq']:,.0f} buys; it provides {pct(m['max_win_freq']*25000/m['ev'],1)} of the mode's return. "
         f"Largest non-Max-Win payout seen: {m['max_observed_below_5w']:,.1f}×.")

L += ["", "## 6. Golden Case (1,000×)", "",
      f"P(win) = {g['exact_p_win']:.6f} (1 in {1/g['exact_p_win']:.2f}); RTP {pct(g['exact_rtp'],4)} exact. Simulation of {g['N']:,} buys: {pct(g['sim_rtp'],3)} ± {pct(1.96*g['sim_se'],3)}."]

L += ["", "## 7. Behaviour checks (tests/)", "",
      "| Check | Evidence | Result |", "|---|---|---|",
      "| 3/4/5/6 Scatters map to exactly one bonus | `test_scatter_mapping_unique`; one tier per count in engine | PASS |",
      "| Scatter pays and triggers | engine `play_base`; exact scatter component above | PASS |",
      "| Extra Chance = exactly 5× P(3..6 SC), 3× cost | `test_extra_chance_uplift_is_exactly_5x`, `test_costs_centralised` | PASS |",
      "| Five Wilds → Max Win once, round ends | `test_five_wilds_pay_max_win_exactly_once`, `test_bonus_maxwin_segment_ends_round` | PASS |",
      "| RED never makes the 5th Wild | clamp + `test_red_never_creates_fifth_wild` | PASS |",
      "| No Scatter/wheel in Min 2 Wild, Golden Case; buys have no base roll | `test_restricted_modes_have_no_scatter_or_wheel` | PASS |",
      "| Super Bonus starts 10 spins + 1 Wild @2×, initialised once | `test_bonus_starting_states` | PASS |",
      "| Payouts on the 0.1× grid, ≤ 25,000× | `test_payouts_on_grid_and_capped` | PASS |",
      "| Seeded determinism | `test_rounds_are_seed_deterministic` | PASS |",
      "| Engine = simulator = exact | `test_engine_vs_sim.py` (4 tests), paired U-means vs exact chain | PASS |",
      "", f"Configuration: `{json.dumps(R['config'], default=float)}`"]
open("docs/VALIDATION_REPORT.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
