# Vice Cartel — Math Specification v2.0 (rebuild)

Status: **calibrated reference model**. Executable source of truth is `vice_cartel_math/config.py` plus `calibrated.py`. Every number below is read from those files or derived from them, and `docs/VALIDATION_REPORT.md` holds the measured results.

Precedence used: (1) the approved corrections of 2026-10-23, (2) the feature CR, (3) the current code as described in the 2026-10-23 audit, (4) the GDD, the PAR v1.1 and older docs. Survival / Lives mode is removed everywhere.

## 1. Global

| Item | Value |
|---|---|
| Grid | 5 reels × 4 rows, 14 fixed paylines (unchanged, table in config) |
| RTP target | 96.40% calibration point; every mode must land in **96.1–96.7%** |
| Max Win | 25,000× base bet, cumulative per round; the round ends the moment it is reached |
| Payout grid | Round total floored to 0.1× (Stake min denomination), floor applied before cap |
| Bet unit | All payouts are in multiples of the **base bet**; RTP denominator = mode cost |

## 2. Symbols, strip, paytable

* Paytable unchanged (H1 0.5/2/6 … L4 0.04/0.12/0.40; 5×W = 6.0). Line rules unchanged: left-to-right, leading Wilds substitute, Scatter breaks a line, the higher of the symbol win and the Wild win is paid.
* **Strip:** the 191-stop BR0 with the 9 SC stops removed → 182 stops. Counts per reel: H1 3, H2 6, H3 10, H4 16, L1 24, L2 32, L3 41, L4 50. Each cell is an independent uniform draw (unchanged mechanism).
* **Why SC left the strip:** with 9/191 per cell, 3+ Scatters occur on 1 in 17 spins, and 3:4:5:6 ratios collapse to about 1 : 0.2 : 0.03 : 0.004. Hitting a 40:20:5:1 ladder at playable frequencies is impossible with any per-cell weight (audit follow-up, exact convolution).

## 3. Base game (cost 1×)

Round order:

1. **Wild reels.** Each reel becomes a full 1×4 Wild independently with probability **p = 5.3455%** (was 4.5%). Each Wild draws its multiplier from the unchanged table (1×…1000×, mean 4.1716).
2. **Five Wilds → Max Win.** If all 5 reels are Wild, pay 25,000×. The round ends: no lines, no Scatter, no bonus. Probability p⁵ = 1 in 2,291,175 (1.09% RTP).
3. **Symbols.** Free cells are drawn from the strip.
4. **Scatters.** The Scatter count *n* is drawn from the table below and placed uniformly on cells of non-Wild reels. It is clamped to the number of free cells, which only binds with 4 Wild reels.
5. **Pay.** Pay = (sum of 14 line wins) × M + Scatter pay. M = sum of Wild multipliers, or 1 with no Wild. Scatter pay is not multiplied: 3 → 0.5×, 4 → 2×, 5 → 5×, 6 → 5×.
6. **Trigger.** Exactly one bonus by count: 3 → Normal, 4 → Super, 5 → Hidden, 6 → Super Hidden. Counts of 7+ cannot be drawn. The trigger spin's win is kept and the bonus is added on top (cumulative cap).

| Scatters *n* | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| P(n), base | 0.8482827 | 0.12 | 0.03 | 0.00104079 | 0.00052039 | 0.00013010 | 0.00002602 |
| 1 in | – | 8.3 | 33 | 961 | 1,922 | 7,686 | 38,432 |

Total trigger probability = 0.0017173 (1 in 582). The tier ratio is 40:20:5:1, the design ratio from the original Mystery weights. 1 and 2 Scatters are cosmetic near-misses.

## 4. Extra Chance (cost 3×)

The board is identical to the base game, and payouts are still in base-bet units. P(3..6 Scatters) is **multiplied by 5**, and P(0) absorbs the difference. Trigger rates become: Normal 1 in 192, Super 1 in 384, Hidden 1 in 1,537, Super Hidden 1 in 7,687, any bonus 1 in 116.5.

**Why 5× and not 3×.** Write B for the non-bonus return and F for the bonus return in the base game. The two constraints are B + F = 0.964 and (B + kF)/3 = 0.964, which give F = 1.928/(k−1). With k = 3 that is F = 0.964 and B = 0, which is impossible. With k = 5, B = F = 0.482. That 48/48 split is also why the Wild probability had to rise from 4.5% to 5.3455%. At 4.5% the base side is only about 0.39, and no strip reshuffle can lift it, because line RTP is insensitive to strip shape.

## 5. Bonus games

Common rules: there are no Scatters on the bonus board and no random Wild roll. Only sticky Wild reels appear. M = sum of sticky multipliers. The 25,000× cumulative cap applies. The safety limit is 200 spins, which is never reached (maximum observed: see report §4). State is initialised once from the tier table, with fresh Wild positions and no carry-over.

| Tier | Trigger | Spins | Start Wilds | Start mult | P(wheel)/spin | MAX WIN weight | Bonus EV (capped) | P(Max Win) per round |
|---|---|---|---|---|---|---|---|---|
| Normal (Vacation Mode) | 3 SC / buy 100× | 10 | 0 | – | **0.303018** | 0.0029254 | 96.4× (target) | see report |
| Super (Big Score) | 4 SC / buy 200× | 10 | 1 | 2× | **0.245693** | 0.0092398 | 192.8× (target) | see report |
| Hidden (Secret Vault) | 5 SC | 12 | 2 | 3× | 0.35 | 0.0414272 | ≈1,469× | see report |
| Super Hidden (Kingpin's Island) | 6 SC | 12 | 3 | 5× | 0.35 | 0.1385452 | ≈3,395× | see report |

### Wheel (bonus only)

Each bonus spin, the wheel spins with the tier's P(wheel). The segment is then drawn from RED 35 / BLUE 40 / YELLOW 25 / **MAX WIN w** (w is the per-tier weight above). The original 35/40/25 RED/BLUE/YELLOW ratio is preserved.

* **RED:** adds 1 Wild reel (2 with probability 10%) on a random non-Wild reel, with a multiplier from the base table. **RED can never create the 5th Wild:** the add is clamped to 4 Wild reels, and at 4 Wilds RED has no effect.
* **BLUE:** one random sticky Wild gains +2…+1000 (unchanged table, mean 5.8457). With no Wild, it has no effect.
* **YELLOW:** +1/+2/+3 spins (60/30/10).
* **MAX WIN (5-Wild icon):** all 5 reels turn Wild, which is five Wilds and therefore Max Win. The round total becomes exactly 25,000× and the round ends immediately. No further wheel results or board evaluation happen. This is the only route to 5 Wilds inside a bonus, which keeps "five Wilds = Max Win" true in every mode while making its probability a single tunable weight.

## 6. Purchased features

| Mode | Cost | Content | Probabilities applied |
|---|---|---|---|
| Normal Bonus buy | 100× | Normal Bonus round only | No base spin, no Scatter draw, no Wild roll, no trigger roll |
| Super Bonus buy | 200× | Super Bonus round only | Same as above |
| Minimum 2 Wild | 100× | One spin with 2 guaranteed Wild reels; each other reel becomes Wild with **q = 13.8188%** | No Scatters, no wheel, no bonus. 5 Wilds = Max Win |
| Golden Case | 1,000× | Unchanged: ≥1 letter guaranteed, all 3 = 25,000× | q = 0.291759, P(win) = 3.852%, RTP 96.3000% exact |

Hidden and Super Hidden are **not** sold. The old 3×/5× Extra Chance pair, the 200×/250× Min 2 Wild pair and Mystery are removed.

Min 2 Wild K mix: 2 → 64.0%, 3 → 30.8%, 4 → 4.93%, 5 → 0.264% (1 in 379). Because 5 Wilds now pays 25,000×, about 68% of this mode's return comes from the Max Win. A price of 150× or 200× would push that share to 75–79%, so 100× is the least top-heavy option.

## 7. Calibration method

1. **Bonus tiers:** an exact Markov chain over (Wild set, turns) tracks probability mass, multiplier-sum mass and accumulated-win mass. The MAX WIN segment is handled exactly. P(wheel) for Normal and Super is solved for the buy targets, then lifted by the paired-path cap/floor loss (Normal +0.19×, Super +0.29×). The MAX WIN weight is solved so that P(segment) per round is Normal 1/10,000, Super 1/4,000, Hidden 1/500 and Super Hidden 1/150.
2. **Base and Extra Chance:** an exact enumeration of line EV per (Wild set, Scatter count), including the Scatters that break lines (hypergeometric). Simulated capped tier EVs and the paired cap/floor correction of plain spins (0.0146 per unit) are added. *p* and the total trigger rate are then solved jointly so that base = Extra Chance = 96.40%.
3. **Min 2 Wild:** exact EV in q, plus the simulated cap and floor loss (−0.08%).

## 8. Changes against the audited code (math effect)

| Area | Was | Now | Reason |
|---|---|---|---|
| Bonus entry | Optimizer-forced books, no in-game trigger | Natural 3/4/5/6-Scatter trigger | CR A, "Optimizer: Natural" |
| Mystery | Optimizer-only fence | Removed | Correction #5 |
| SC on strip | 9/191 per cell | Off strip; count table | Ladder infeasible (§2) |
| Wild reel prob | 4.5% | 5.3455% | Extra Chance feasibility (§4) |
| 5 Wilds | 84×M line win (≤420,000× capped) | Max Win, round ends | CR C |
| Bonus wheel | RED/BLUE/YELLOW, 35% | + MAX WIN segment, per-tier P(wheel); RED clamped at 4 Wilds | CR C/D, corrections #1 and #6 |
| Extra Chance | 3× and 5× modes, identical books | One mode: 3× cost, 5× Scatter chance | Correction #2 |
| Bonus buys | None (removed) | Normal 100×, Super 200× | Correction #3 |
| Min 2 Wild | 200× / 250×, q = 0.3976 / 0.4412 | 100×, q = 0.138188 | Correction #4, 5W rule |
| Scatter pay | Paid, no trigger | Paid and triggers | CR A (pay + trigger kept) |
