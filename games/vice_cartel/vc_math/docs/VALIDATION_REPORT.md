# Vice Cartel — Validation Report

Required RTP range **96.1%–96.7%**; calibration target 96.4%. All CIs are 95% (±1.96 SE). Every simulated payout is capped at 25,000× and floored to 0.1× exactly as the game pays.

**Primary estimator:** the exact value (no randomness, cap and floor ignored) plus a simulated cap/floor correction. The correction is measured on paired paths: the same random draws are played with and without the cap. **Independent checks:** direct simulation of fully played rounds.

## 1. RTP by mode

| Mode | Cost | Exact (pre-cap, pre-floor) | Final RTP (exact + correction) | 95% CI | Direct simulation (check) | Check 95% CI | Status |
|---|---:|---:|---:|---|---:|---|---|
| base | 1× | 98.002% | **96.399%** | [96.388%, 96.409%] | 95.33% (20M spins) | [93.29%, 97.37%] | PASS |
| extra_chance | 3× | 97.119% | **96.398%** | [96.380%, 96.416%] | 95.59% (20M spins) | [94.16%, 97.01%] | PASS |
| bonus_normal | 100× | 96.592% | **96.399%** | [96.320%, 96.479%] | 96.52% (2M rounds) | [95.84%, 97.19%] | PASS |
| bonus_super | 200× | 96.544% | **96.385%** | [96.346%, 96.424%] | 96.06% (2M rounds) | [95.59%, 96.54%] | PASS |
| min2wild | 100× | 96.483% | **96.446%** (stratified by exact P(K)) | [96.394%, 96.498%] | 96.52% raw mean (10M) | – | PASS |
| golden_case | 1000× | 96.3000% | **96.3000%** (exact, no cap/floor effect) | exact | 96.276% (20M) | [96.07%, 96.49%] | PASS |

## 2. Base and Extra Chance breakdown (per unit of cost)

| Component | Base | Extra Chance (÷3) |
|---|---:|---:|
| lines (exact) | 48.529% | 16.119% |
| scatter (exact) | 0.234% | 0.390% |
| five_wilds (exact) | 1.091% | 0.364% |
| normal_bonus (exact) | 10.053% | 16.755% |
| super_bonus (exact) | 10.048% | 16.747% |
| hidden_bonus (exact) | 19.184% | 31.973% |
| super_hidden_bonus (exact) | 8.863% | 14.771% |
| cap + 0.1× floor on non-bonus spins (sim) | -1.461% | -0.484% |
| cap + floor inside bonuses (sim) | -0.143% | -0.238% |
| **Total** | **96.399%** | **96.398%** |

Modelling bound: the floor on (trigger spin + bonus) versus the floor on the bonus alone differs by less than 0.017% (base) and 0.029% (EC).
Base split: non-bonus 48.39% / bonus 48.01%.

## 3. Trigger and Max Win frequencies

| Event | Base P per spin | Base 1 in | Extra Chance 1 in |
|---|---:|---:|---:|
| 3 Scatters → normal_bonus | 1.0408e-03 | 961 | 192 |
| 4 Scatters → super_bonus | 5.2040e-04 | 1,922 | 384 |
| 5 Scatters → hidden_bonus | 1.3009e-04 | 7,687 | 1,537 |
| 6 Scatters → super_hidden_bonus | 2.6019e-05 | 38,434 | 7,687 |
| any bonus | 1.7173e-03 | 582 | 116 |
| five Wilds (Max Win) | 4.3646e-07 | 2,291,175 | 2,291,175 |
| any 25,000× Max Win | 1.2428e-06 | 804,609 | 223,795 |

Direct check: 20,000,000 base spins gave 34,080 bonuses (expected 34,346) and 22 Max Wins (expected 24.9). 20,000,000 Extra Chance spins gave 171,828 bonuses (expected 171,730) and 82 Max Wins (expected 89.4). Volatility (SD per unit cost): base 46.6, Extra Chance 97.4.

## 4. Bonus tiers

| Tier | Exact EV (uncapped) | Final EV (exact + correction) | 95% CI | Direct sim EV (2M) | SD | Avg spins exact / sim | Max spins seen | P(Max Win) | MAX WIN segment exact / sim | P(round pays 0) |
|---|---:|---:|---|---:|---:|---|---:|---|---|---:|
| normal_bonus | 96.59× | **96.40×** | [96.32, 96.48] | 96.52× | 485 | 11.281 / 11.281 | 29 | 1 in 8,403 | 1 in 10,000 / 1 in 9,524 | 2.095% |
| super_bonus | 193.09× | **192.77×** | [192.69, 192.85] | 192.13× | 691 | 11.013 / 11.013 | 27 | 1 in 3,521 | 1 in 4,000 / 1 in 3,922 | 0.302% |
| hidden_bonus | 1474.60× | **1468.77×** | [1468.36, 1469.18] | 1471.06× | 2117 | 13.799 / 13.797 | 34 | 1 in 393 | 1 in 500 / 1 in 495 | 0.009% |
| super_hidden_bonus | 3406.30× | **3394.69×** | [3394.11, 3395.27] | 3392.98× | 2897 | 13.767 / 13.763 | 38 | 1 in 127 | 1 in 150 / 1 in 149 | 0.000% |

## 5. Minimum 2 Wild (100×)

| Wild reels | P exact | E[pay] simulated |
|---:|---:|---:|
| 2 | 0.64008 | 8.03× |
| 3 | 0.30790 | 45.10× |
| 4 | 0.04937 | 231.91× |
| 5 | 0.00264 | 25,000.00× |

Max Win (5 Wilds) 1 in 379 buys; it provides 68.4% of the mode's return. Largest non-Max-Win payout seen: 21,758.0×.

## 6. Golden Case (1,000×)

P(win) = 0.038520 (1 in 25.96); RTP 96.3000% exact. Simulation of 20,000,000 buys: 96.276% ± 0.211%.

## 7. Behaviour checks (tests/)

| Check | Evidence | Result |
|---|---|---|
| 3/4/5/6 Scatters map to exactly one bonus | `test_scatter_mapping_unique`; one tier per count in engine | PASS |
| Scatter pays and triggers | engine `play_base`; exact scatter component above | PASS |
| Extra Chance = exactly 5× P(3..6 SC), 3× cost | `test_extra_chance_uplift_is_exactly_5x`, `test_costs_centralised` | PASS |
| Five Wilds → Max Win once, round ends | `test_five_wilds_pay_max_win_exactly_once`, `test_bonus_maxwin_segment_ends_round` | PASS |
| RED never makes the 5th Wild | clamp + `test_red_never_creates_fifth_wild` | PASS |
| No Scatter/wheel in Min 2 Wild, Golden Case; buys have no base roll | `test_restricted_modes_have_no_scatter_or_wheel` | PASS |
| Super Bonus starts 10 spins + 1 Wild @2×, initialised once | `test_bonus_starting_states` | PASS |
| Payouts on the 0.1× grid, ≤ 25,000× | `test_payouts_on_grid_and_capped` | PASS |
| Seeded determinism | `test_rounds_are_seed_deterministic` | PASS |
| Engine = simulator = exact | `test_engine_vs_sim.py` (4 tests), paired U-means vs exact chain | PASS |

Configuration: `{"p_wild": 0.053455, "trigger_total": 0.0017173, "scatter_p": {"3": 0.0010407878787878789, "4": 0.0005203939393939394, "5": 0.00013009848484848486, "6": 2.601969696969697e-05}, "min2wild_q": 0.138188, "wheel": {"normal_bonus": [0.303018, 0.0029254], "super_bonus": [0.245693, 0.0092398], "hidden_bonus": [0.35, 0.0414272], "super_hidden_bonus": [0.35, 0.1385452]}}`
