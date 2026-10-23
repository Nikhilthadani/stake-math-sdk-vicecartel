# Vice Cartel — Change Report, Root Causes and Porting Guide

## 1. Root causes found in the audited implementation

| # | Root cause | Effect | Fix in this rebuild |
|---|---|---|---|
| RC1 | Bonuses were reachable only through optimizer-forced `freegame` books. Scatters never triggered anything. | Bonus frequency and tier mix were set by lookup weights, not by gameplay. The configured "mystery" probabilities had no runtime effect. | Natural Scatter trigger with an exact count table (MATH_SPEC §3) |
| RC2 | SC sat on the strip at 9/191 per cell. | A 3/4/5/6 ladder on that strip would trigger on 1 in 17 spins, roughly 1,200% RTP. | SC removed from the strip and placed by a count table |
| RC3 | base / extra_chance_3x / extra_chance_5x used byte-identical books. | "Extra Chance" changed nothing inside a round. | Extra Chance now multiplies P(3..6 Scatters) by 5 inside the round |
| RC4 | Bonus Buys were removed. Bonus probabilities and the triggering base spin still applied to forced bonus books. | A purchase could not be priced; it inherited base-game probabilities. | Buy = bonus round only; no base spin, Scatter, Wild or trigger roll (`engine.play_bonus_buy`, tests) |
| RC5 | Optimizer fence targets came from a measured 548.1× "per mystery check". The natural uncapped bonus EV was 899×, so the gap was hidden by reweighting. | The deployed bonus distribution did not match the configured game. | Exact Markov chain plus simulation, no reshaping |
| RC6 | The Min 2 Wild comment claimed 96.35%; exact values were 96.63% / 96.58%. Five Wilds paid only 84×M. | The comment was not reproducible; the new 5W rule would push RTP to 786% at the old settings. | 100×, q = 0.138188, 5W = Max Win |
| RC7 | PAR v1.1 described Survival, scatter-cosmetic, a 130-weight strip and 96.00%. | The documentation disagreed with the code. | PAR superseded by MATH_SPEC v2.0 |
| RC8 | `include_padding_index` mismatch in `winInfo` positions; `updateFreeSpin` always sent 0/0 (audit R5 and D8). | Frontend only. | Not math; flagged for the frontend owner |

## 2. Files in this package

| File | Purpose |
|---|---|
| `vice_cartel_math/config.py` | Single source of every rule, table, cost and visibility flag |
| `vice_cartel_math/calibrated.py` | The 9 solved numbers; nothing else may hardcode them |
| `vice_cartel_math/engine.py` | Scalar seeded per-round engine — the logic to port into the SDK |
| `vice_cartel_math/sim.py` | Vectorized simulator; same rules, cross-checked against the engine |
| `vice_cartel_math/exact.py` | Exact line EV, exact bonus Markov chain, exact base/EC/Min 2 Wild/Golden |
| `vice_cartel_math/calibrate.py` | Re-solves wheel parameters from targets |
| `vice_cartel_math/validate.py`, `report.py` | Full validation run → `reports/validation.json` → `docs/VALIDATION_REPORT.md` |
| `vice_cartel_math/books.py` | Natural stratified lookup weights (§4) |
| `tests/` | Rule tests, determinism, five-Wild-once, restricted modes, engine vs simulator, engine vs exact, book weighting (17 tests) |

## 3. Porting map into `stake-math-sdk-vicecartel`

| SDK file (from audit) | Change |
|---|---|
| `game_config.py` | Import values from `config.py`/`calibrated.py`. Drop SC from `BR0.csv` (182 stops). Set `PER_REEL_WILD_PROB = 0.053455`. Delete `MYSTERY_*`, `BASE_ONLY_RTP`, `BASE_HIT_RATE`, `MIN2WILD_EXTRA_PROB_200X/_250X`. Bet modes: `base` 1, `extra_chance` 3, `bonus_normal` 100, `bonus_super` 200, `min2wild` 100, `golden_case` 1000; `rtp = 0.964`. |
| `game_executables.py` | `draw_wild_board`: on 5 Wild reels, award wincap and stop. New `place_scatters(n)` on free cells. `resolve_wheel`: MAX WIN segment, RED clamp at 4, per-tier `wheel_prob`. `draw_min2wild_board(q)`: 5 Wilds → wincap. |
| `gamestate.py` | Remove `_forced_mystery_outcome` and the `force_freegame` path. Trigger by Scatter count (one tier). Buy modes call `run_bonus(tier)` directly with no base spin. Follow `engine.py` order exactly. |
| `game_override.py` | Tier setup reads `BONUS_TIERS`. Keep 0.1× flooring. `check_repeat` is no longer needed for natural books. |
| `game_optimization.py`, `run.py` | Do **not** run the optimizer (correction #7). Generate stratified books and weight them with `books.py` (see §4). |
| `game_events.py` | Emit a `wheelSpin` result of `MAX_WIN` (5-Wild icon) and a `fiveWilds` event. Presentation only. |

## 4. Production: natural books and deployed RTP

On Stake, the deployed RTP **is the weighted mean of the published lookup table**, not the theoretical value. With no optimizer and unweighted books, sampling noise decides the shipped RTP. To keep each outcome class within ±0.05% RTP, unweighted books would need:

| Mode | Class | Exact P | SD | Unweighted books for ±0.05% |
|---|---|---:|---:|---:|
| base | plain spin | 0.99828 | 5.57 | ~124M |
| base | Normal / Super / Hidden / Super Hidden | 1/961 … 1/38,434 | 485 … 2,897 | 1.0M / 0.52M / 0.30M / 23k |
| extra_chance | plain spin | 0.99141 | 5.52 | ~13M |
| bonus_normal | whole mode | 1 | 485 | ~94M |
| bonus_super | whole mode | 1 | 691 | ~48M |

**Recommended method: natural stratified weights** (`vice_cartel_math/books.py`, tested):

1. Generate books per outcome class with the engine:
   - base and Extra Chance: plain spins (ideally split by Wild-reel count K = 0..4), five Wilds (one book), and each of the 4 tiers;
   - each buy mode as a single class.
2. Set each class's total weight to its **exact** probability (`VALIDATION_REPORT` §3, or `exact.base_components`).
3. Inside a class, apply the minimum-χ² linear tilt w = 1 + λ(x − mean). This moves the sample mean onto the validated class mean (`VALIDATION_REPORT` §4, final EV). Measured with 1M books: max/min weight ratio is 1.058 for Normal and 1.006 for Super, so the shape stays natural. `tilt()` refuses (raises) if any weight would be ≤ 0; then generate more books.
4. Recompute the deployed RTP from the lookup table (`books.deployed_rtp`). Ship only if it is 96.40% ± 0.05%.

This is not the old optimizer. Class probabilities are the game's own natural ones, and the tilt is only as large as the sampling error.

## 5. Open questions and decisions to confirm

1. **Wild reel probability 4.5% → 5.3455%.** This is forced by "Extra Chance = 3× cost with 3× or 5× chance": 3× is infeasible and 5× needs a 48/48 base/bonus split. Base five-Wild Max Win moves from 1 in 5.42M to 1 in 2.29M (1.09% RTP). The alternative is to keep 4.5% and allow a non-integer uplift of about 4.5×.
2. **RED at 4 Wild reels has no effect**, so that 5 Wilds in a bonus only come from the MAX WIN segment. The alternative is to convert RED at 4 Wilds into a BLUE upgrade; that is EV-neutral after re-solving.
3. **Wheel frequency now differs by tier:** Normal 30.3%, Super 24.6%, Hidden/Super Hidden 35%. Super spins the wheel less often than Normal because it starts with a Wild. Confirm the UI can show per-tier trigger odds.
4. **Hidden and Super Hidden are not buyable.** If a price is wanted: EV is about 1,471× and 3,393×, so 96.4% RTP means prices of about 1,526× and 3,520×.
5. **MAX WIN segment visual size:** the probability is set by weight (≈0.003–0.14%), not by arc size. Confirm with compliance that a visible segment much larger than its probability is acceptable in your target jurisdictions, or size the arc to the weight.
6. **Golden Case** stays at 96.3000% exact (inside the range). Weight it as two exact classes (win 3.852002%, no win), so the deployed RTP equals 96.3000% exactly, whatever the number of books.
7. Frontend items RC8 are outside math scope.
