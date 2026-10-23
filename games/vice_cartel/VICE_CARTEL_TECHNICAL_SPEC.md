# Vice Cartel — Technical Specification

> **Outdated (math v1).** The live math is v2.0: see `vc_math/docs/MATH_SPEC.md` for the math and
> `frontend/FRONTEND_INTEGRATION.md` for modes, events and config.

**Target RTP 96.30% | Max Win 25,000x | 5×4 Grid | 14 Paylines | 6 Bet Modes**

All numbers below come from `game_config.py` or the published run (1,000,000 books per mode,
`library/statistics_summary.json` and `library/stats_summary.json`).
For a step-by-step walk-through of the code, see `VICE_CARTEL_PSEUDOCODE.md`.

---

## 0. TRIGGER SUMMARY

| Feature | Trigger | Code |
|---------|---------|------|
| Line win | 3+ matching symbols left-to-right on a payline (W substitutes) | `evaluate_lines_with_wilds` |
| Full-Reel Wild | `random() < 4.5%` per reel, per base spin | `is_reel_wild` |
| Spin multiplier | Any Wild reel on the board (sum of multipliers, applied if > 1) | `compute_spin_multiplier` |
| Scatter pay | 3+ `SC` anywhere (base, Extra Chance, Min 2 Wild) | `evaluate_scatter_pay` |
| Mystery check / Bonus | Book is in the `freegame` distribution (`force_freegame`); optimizer sets frequency | `_forced_mystery_outcome` |
| Bonus tier | Weighted pick 40 / 20 / 5 / 1 when the mystery check fires | `_forced_mystery_outcome` |
| Bonus Wheel | `random() < 35%` before each bonus spin | `wheel_triggers` |
| RED / BLUE / YELLOW | Weighted pick 35 / 40 / 25 when the Wheel triggers | `wheel_segment` |
| Golden Case | Bet mode `golden_case` (buy 1,000x) | `run_golden_case` |
| Extra Chance | Bet mode `extra_chance_3x` / `extra_chance_5x` (3x / 5x per spin) | same path as `base` |
| Min 2 Wild | Bet mode `min2wild_200x` / `min2wild_250x` (buy) | `draw_min2wild_board` |
| Max win | Running win reaches 25,000x, or 3 letters in Golden Case; bonus loop stops | `evaluate_wincap` |

---

## 1. BASE GAME

### Grid & Symbols
- 5 reels × 4 rows = 20 visible positions
- 8 paying symbols: H1, H2, H3, H4 (premium), L1, L2, L3, L4 (low)
- 2 special symbols: W (Wild), SC (Scatter)
- Wild occupies an **entire reel** (all 4 rows), substitutes for all paying symbols

### Reel Strip (`reels/BR0.csv`, 191 stops, identical on all 5 reels)
Each of the 4 cells on a reel is drawn **independently** from the strip.

| Symbol | Stops | Probability |
|--------|-------|-------------|
| H1     | 3     | 1.57%       |
| H2     | 6     | 3.14%       |
| H3     | 10    | 5.24%       |
| H4     | 16    | 8.38%       |
| L1     | 24    | 12.57%      |
| L2     | 32    | 16.75%      |
| L3     | 41    | 21.47%      |
| L4     | 50    | 26.18%      |
| SC     | 9     | 4.71%       |

### Paytable (× total bet, per winning line)
| Symbol | 3-of-a-kind | 4-of-a-kind | 5-of-a-kind |
|--------|-------------|-------------|-------------|
| W      | —           | —           | 6.00 (pays as H1) |
| H1     | 0.50        | 2.00        | 6.00        |
| H2     | 0.35        | 1.20        | 4.00        |
| H3     | 0.25        | 0.80        | 2.50        |
| H4     | 0.15        | 0.50        | 1.50        |
| L1     | 0.10        | 0.30        | 1.00        |
| L2     | 0.08        | 0.25        | 0.80        |
| L3     | 0.05        | 0.15        | 0.50        |
| L4     | 0.04        | 0.12        | 0.40        |

### 14 Paylines (row index 0-3, top=0)
| Line | R1 | R2 | R3 | R4 | R5 |
|------|----|----|----|----|-----|
| 1    | 0  | 0  | 0  | 0  | 0   |
| 2    | 1  | 1  | 1  | 1  | 1   |
| 3    | 2  | 2  | 2  | 2  | 2   |
| 4    | 3  | 3  | 3  | 3  | 3   |
| 5    | 0  | 1  | 2  | 1  | 0   |
| 6    | 3  | 2  | 1  | 2  | 3   |
| 7    | 1  | 0  | 1  | 0  | 1   |
| 8    | 2  | 3  | 2  | 3  | 2   |
| 9    | 0  | 1  | 1  | 1  | 0   |
| 10   | 3  | 2  | 2  | 2  | 3   |
| 11   | 1  | 2  | 1  | 2  | 1   |
| 12   | 2  | 1  | 2  | 1  | 2   |
| 13   | 0  | 1  | 2  | 3  | 2   |
| 14   | 3  | 2  | 1  | 0  | 1   |

### Full-Reel Wild Mechanic
**Trigger:** independent 4.5% roll per reel on every base / Extra Chance spin. Not a landing symbol.
```
For each of 5 reels independently:
  Roll: 4.5% → entire reel becomes Wild (all 4 rows = W)
  If Wild: draw multiplier from WILD_MULTIPLIER_WEIGHTS table

Wild count distribution (binomial, p = 4.5%):
  0 Wilds: 79.43%  |  1 Wild: 18.71%  |  2 Wilds: 1.76%
  3 Wilds: 0.083%  |  4 Wilds: 0.002% |  5 Wilds: 0.00002%
```

### Wild Multiplier Distribution
| Multiplier | Weight | Probability |
|------------|--------|-------------|
| 1x         | 3000   | 33.81%      |
| 2x         | 2200   | 24.79%      |
| 3x         | 1600   | 18.03%      |
| 5x         | 1000   | 11.27%      |
| 10x        | 500    | 5.63%       |
| 15x        | 260    | 2.93%       |
| 20x        | 150    | 1.69%       |
| 25x        | 90     | 1.01%       |
| 50x        | 40     | 0.45%       |
| 75x        | 18     | 0.20%       |
| 100x       | 9      | 0.10%       |
| 150x       | 4      | 0.045%      |
| 200x       | 2      | 0.023%      |
| 250x       | 1      | 0.011%      |
| 500x       | 0.3    | 0.003%      |
| 1000x      | 0.02   | 0.0002%     |

**Expected value of a new Wild's multiplier = 4.172x**

### Multiplier Application Rule
```
spin_multiplier = SUM of multiplier values of ALL Wild reels on the board   (no Wilds → 1)
total_line_win  = (sum of all 14 payline wins) × spin_multiplier

Applied ONCE to the line total, NOT per line. Scatter pay is NOT multiplied.
```

### Scatter Pay (separate from paylines, anywhere on screen)
**Trigger:** 3 or more `SC` anywhere on the board.

| SC Count | Payout |
|----------|--------|
| 3        | 0.5x   |
| 4        | 2.0x   |
| 5+       | 5.0x   |

- Scatter does NOT participate in payline matching. Scatter breaks a payline run.
- Scatter **only pays** — it does NOT trigger the bonus.
- Scatter pays in base, Extra Chance and Min 2 Wild spins. It does **not** pay during bonus spins.

### Base Game RTP: **39.24%** per 1x bet
40.58% exact, minus 1.34% lost to the 0.1x payout flooring (see §9). Non-zero win: 1 in 3.44 spins.

---

## 2. MYSTERY TRIGGER SYSTEM

**Trigger:** hidden random check after a base or Extra Chance spin. No symbol, scatter count or buy is involved.
Never runs in Golden Case or Min 2 Wild.

```
After the base spin is evaluated:
  Mystery check: P = 0.1041% (1-in-961 spins)
  If fires → draw outcome from weighted table:
    Normal Bonus:        40   →  1-in-2,401 spins
    Super Bonus:         20   →  1-in-4,802 spins
    Hidden Bonus:         5   →  1-in-19,206 spins
    Super Hidden Bonus:   1   →  1-in-96,032 spins
    No Bonus:            34   →  nothing happens

  Any bonus: 1-in-1,455 spins (published)
```

**How it is implemented:** the trigger is not rolled live inside a normal spin.
- Bonus rounds are only simulated in books of the `freegame` distribution (`force_freegame = True`).
- In those books, `_forced_mystery_outcome()` picks one of the 4 bonus tiers by the weights above (No Bonus excluded) and emits `mysteryTrigger`.
- The optimizer then weights the `freegame` books to hit rate `1 / (MYSTERY_TRIGGER_PROB × 66%)` = 1 in 1,455.
- `MYSTERY_TRIGGER_PROB` is solved as `(0.963 × cost − 0.3924) / 548.1x`, where 548.1x is the EV per mystery check.

---

## 3. BONUS WHEEL SYSTEM

**Trigger:** 35% roll before each bonus spin, in all 4 tiers. Never in the base game.

```
Per bonus spin:
  Roll: 35% chance Wheel triggers
  If triggers → draw segment:
    RED    (35%): Add sticky Wild(s)
    BLUE   (40%): Upgrade existing Wild multiplier
    YELLOW (25%): Add extra spins
```

### RED — Add Sticky Wild
**Trigger:** Wheel lands RED (35%).
```
Pick from reels that are not already Wild
Add 1 new sticky Wild reel (90% of the time)
Add 2 new sticky Wilds (10% of the time, capped by empty reels left)
Each new Wild's multiplier drawn from WILD_MULTIPLIER_WEIGHTS (same as base game)
```

### BLUE — Upgrade Wild Multiplier
**Trigger:** Wheel lands BLUE (40%) and at least 1 sticky Wild exists.
```
Pick 1 random existing sticky Wild reel
Add increment drawn from BLUE_INCREMENT_WEIGHTS:
  +2x (38.2%), +3x (26.5%), +5x (16.2%), +10x (8.8%), +15x (4.7%)
  +20x (2.8%), +25x (1.6%), +50x (0.7%), +75x (0.3%), +100x (0.15%)
  +150x (0.07%), +200x (0.03%), +250x (0.015%), +500x (0.004%), +1000x (0.0003%)
If no Wilds exist yet → no effect this spin
```

### YELLOW — Extra Spins
**Trigger:** Wheel lands YELLOW (25%).
```
  +1 spin: 60%
  +2 spins: 30%
  +3 spins: 10%
```

---

## 4. BONUS TIERS

**Trigger:** the mystery check fires (§2) and its weighted pick lands on that tier.

All 4 tiers use the same engine (sticky Wilds + Wheel) and are **spins only**. They differ in starting state.

| Tier               | Spins | Starting Wilds | Start Multiplier (each) | Frequency (base) |
|--------------------|-------|----------------|-------------------------|------------------|
| Normal Bonus       | 10    | 0              | —                       | 1-in-2,401       |
| Super Bonus        | 10    | 1              | 2x                      | 1-in-4,802       |
| Hidden Bonus       | 12    | 2              | 3x                      | 1-in-19,206      |
| Super Hidden Bonus | 12    | 3              | 5x                      | 1-in-96,032      |

```
Bonus loop (run_bonus):
  Place starting Wilds on random reels
  While spins left > 0 AND 25,000x cap not hit AND spins played < 200 (safety cap):
    1. Wheel check (may add Wilds, upgrade a multiplier, or add spins)
    2. Draw board, overlay sticky Wilds as full Wild reels
    3. Line wins × SUM of sticky Wild multipliers (no scatter pay)
    4. spins left −= 1
```

**Average bonus win (all tiers combined, published): 830.5x.** Bonus RTP in base mode: 57.06%.

---

## 5. GOLDEN CASE (Buy Feature)

**Trigger:** player buys bet mode `golden_case`. The 25,000x win needs all 3 letters.

```
Cost:           1,000x total bet
Mechanic:       One reveal of 3 letters: M, A, X
Per-letter P:   29.1759% each, independent
Guarantee:      At least 1 letter always lands (re-rolled until ≥ 1)
Win condition:  All 3 letters → 25,000x instant win
Miss:           1 or 2 letters → 0 payout
P(win):         0.291759³ / (1 − 0.708241³) = 3.852% (1-in-25.96)
RTP:            3.852% × 25,000 / 1,000 = 96.30%
```

Published 1M-book run: 96.5% RTP, win 1-in-25.9 (sampling noise). Published unweighted (no optimization).

---

## 6. EXTRA CHANCE (Buy Feature)

**Trigger:** player buys bet mode `extra_chance_3x` or `extra_chance_5x`, per spin. Bonuses inside it still come from the mystery check.

Same base game and bonus mechanics. Only the mystery trigger probability changes.

| Price | Mystery Check P | Check 1-in-X | Bonus 1-in-X | Base RTP | Bonus RTP | Total |
|-------|-----------------|--------------|--------------|----------|-----------|-------|
| 1x (base) | 0.1041%     | 961          | 1,455        | 39.24%   | 57.06%    | 96.30% |
| 3x    | 0.4555%         | 220          | 333          | 13.08%   | 83.22%    | 96.30% |
| 5x    | 0.8069%         | 124          | 188          | 7.85%    | 88.45%    | 96.30% |

Payouts reference the standard 1x bet unit, not the elevated price, so base RTP is divided by the cost.

---

## 7. MINIMUM 2 WILD SPIN (Buy Feature)

**Trigger:** player buys bet mode `min2wild_200x` or `min2wild_250x`. The 2 Wild reels are forced; each other reel then rolls 39.76% / 44.12%.

```
Single spin: 2 random reels forced Wild (with multipliers) + extra-wild chance on the remaining 3.
Lines + scatter evaluated as a normal spin. No mystery check / no bonus.
Payouts reference standard 1x bet unit. Published unweighted (no optimization).
```

| Price | Extra-Wild P (per remaining reel) | Published Avg Win | RTP    | Wild Mix (2/3/4/5) |
|-------|-----------------------------------|-------------------|--------|---------------------|
| 200x  | 39.76%                            | 192.65x           | 96.30% | 22/43/29/6%         |
| 250x  | 44.12%                            | 240.83x           | 96.30% | 17/41/33/9%         |

---

## 8. RTP SUMMARY (published)

| Mode             | Cost  | RTP    |
|------------------|-------|--------|
| base             | 1x    | 96.30% |
| extra_chance_3x  | 3x    | 96.30% |
| extra_chance_5x  | 5x    | 96.30% |
| min2wild_200x    | 200x  | 96.30% |
| min2wild_250x    | 250x  | 96.30% |
| golden_case      | 1000x | 96.30% target (96.5% in 1M-book sample) |

---

## 9. PAYOUT ROUNDING

The RGS pays rounds in 0.1x steps. In `evaluate_finalwin` the round total is floored to a multiple of 0.1x;
the cut-off amount is taken from bonus wins first, then base wins. The total is then capped at 25,000x.

---

## 10. IMPLEMENTATION STEPS

### Where each piece lives
| File | What it does |
|------|--------------|
| `game_config.py` | All probabilities, paytable, paylines, reels, bet modes and distributions |
| `game_calculations.py` | Pure random draws: Wild roll, multipliers, wheel segment, scatter count, Golden Case letters |
| `game_executables.py` | Board drawing, line + scatter evaluation, wheel resolution, bonus spin, Golden Case |
| `game_override.py` | Bonus tier setup, 0.1x flooring, repeat rules for forced bonus books |
| `gamestate.py` | `run_spin` per mode, `run_bonus` loop, forced mystery outcome |
| `game_events.py` | Custom frontend events |
| `game_optimization.py` | Optimizer targets for base and Extra Chance |
| `run.py` | Runs the full pipeline |

### Pipeline (`run.py`)
1. **Delete stale publish tables** for every mode, so old lookup tables can't point at new books.
2. **Simulate books**: 1,000,000 per mode, 10 threads, batches of 5,000, compressed output.
   - base / Extra Chance books split into `freegame` (10%), `0` zero-win (40%) and `basegame` (50%).
   - A book is re-simulated until it matches its criteria (e.g. `freegame` books must contain a bonus).
3. **Write configs** (`generate_configs`).
4. **Optimize** `base`, `extra_chance_3x`, `extra_chance_5x` (Rust, 20 threads):
   - `freegame` fence → bonus RTP at hit rate 1-in-1,455 / 333 / 188
   - `basegame` fence → base RTP at hit rate 1-in-3.44
   - `0` fence → zero-win books take the remaining weight
   - Golden Case and Min 2 Wild are **not** optimized; their natural books are published as-is.
5. **Write configs again** with the optimized weights.
6. **Analysis** → `statistics_summary.json`, `stats_summary.json`, `vice_cartel_full_statistics.xlsx`.
7. **RGS format checks** (`execute_all_tests`).

### Status
| Feature | Code | Simulated | Optimized | Published mode |
|---------|:----:|:---------:|:---------:|:--------------:|
| Base Game + Wilds + Scatter | ✅ | ✅ 1M | ✅ | `base` |
| 4 Bonus Tiers + Wheel | ✅ | ✅ | ✅ | inside `base` / Extra Chance |
| Extra Chance 3x / 5x | ✅ | ✅ 1M | ✅ | `extra_chance_3x`, `extra_chance_5x` |
| Golden Case | ✅ | ✅ 1M | — (natural) | `golden_case` |
| Min 2 Wild 200x / 250x | ✅ | ✅ 1M | — (natural) | `min2wild_200x`, `min2wild_250x` |

---

## 11. EVENT CONTRACT (Frontend Integration)

| Event Type | Fields | When |
|------------|--------|------|
| `reveal` | `board[][]`, `gameType`, `paddingPositions`, `anticipation` | Every spin (base and bonus) |
| `wildReel` | `reel`, `multiplier` | A reel becomes Wild (base, Min 2 Wild) |
| `spinMultiplier` | `multiplier` | Combined multiplier > 1 |
| `winInfo` | `totalWin`, `wins[{symbol, kind, win, positions, meta}]` | Line wins |
| `setWin` | `amount`, `winLevel` | After a winning evaluation |
| `setTotalWin` | `amount` | Running total update |
| `scatterPay` | `count`, `payout` (×100) | 3+ scatters anywhere |
| `mysteryTrigger` | `outcome` (tier name) | Bonus starts |
| `updateFreeSpin` | `amount`, `total` | Start of each bonus spin |
| `wheelSpin` | `result` + RED `newWilds{reel: mult}` / BLUE `reel`, `increment`, `newMult` / YELLOW `extraTurns` | Wheel triggers in bonus |
| `stickyWildUpdate` | `wildReels{reel: mult}` | After every wheel spin |
| `freeSpinEnd` | `amount`, `winLevel` | Bonus round ends |
| `goldenCaseReveal` | `lettersLanded` (1-3), `maxWin` (bool) | Golden Case |
| `finalWin` | `amount` | Last event of every book |
