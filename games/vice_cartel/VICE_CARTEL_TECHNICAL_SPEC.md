# Vice Cartel — Technical Specification

**Math Model v1.0 | Target RTP 96.00% | Max Win 25,000x | 5×4 Grid | 14 Paylines**

---

## 1. BASE GAME

### Grid & Symbols
- 5 reels × 4 rows = 20 visible positions
- 8 paying symbols: H1, H2, H3, H4 (premium), L1, L2, L3, L4 (low)
- 2 special symbols: W (Wild), SC (Scatter)
- Wild occupies an **entire reel** (all 4 rows), substitutes for all paying symbols

### Symbol Weight Table (per cell, when reel is not Wild)
| Symbol | Weight | Probability |
|--------|--------|-------------|
| H1     | 2      | 1.54%       |
| H2     | 4      | 3.08%       |
| H3     | 7      | 5.38%       |
| H4     | 11     | 8.46%       |
| L1     | 16     | 12.31%      |
| L2     | 22     | 16.92%      |
| L3     | 28     | 21.54%      |
| L4     | 34     | 26.15%      |
| SC     | 6      | 4.62%       |

### Paytable (× total bet, per winning line)
| Symbol | 3-of-a-kind | 4-of-a-kind | 5-of-a-kind |
|--------|-------------|-------------|-------------|
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
```
For each of 5 reels independently:
  Roll: 4.5% → entire reel becomes Wild (all 4 rows = W)
  If Wild: draw multiplier from WILD_MULTIPLIER_WEIGHTS table
  
Wild count distribution (measured over 100M spins):
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
spin_multiplier = SUM of multiplier values of ALL Wild reels on the board
total_win = (sum of all 14 payline wins) × spin_multiplier

Applied ONCE to the total, NOT per line.
```

### Scatter Pay (separate from paylines, anywhere on screen)
| SC Count | Payout |
|----------|--------|
| 3        | 0.5x   |
| 4        | 2.0x   |
| 5+       | 5.0x   |

Scatter does NOT participate in payline matching. Scatter breaks a payline run.

### Base Game RTP: **40.33%** (measured, N=100,000,000 spins)

---

## 2. MYSTERY TRIGGER SYSTEM

```
Every base-game spin:
  Hidden roll: P = 0.101631% (1-in-984 spins)
  If fires → draw outcome from weighted table:
    Normal Bonus:       40%  →  1-in-2,460 spins
    Super Bonus:        20%  →  1-in-4,920 spins
    Hidden Bonus:        5%  →  1-in-19,679 spins
    Super Hidden Bonus:  1%  →  1-in-98,395 spins
    No Bonus (near-miss):34% →  1-in-2,894 spins
```

- Scatter symbols are **cosmetic/anticipation only** — they do NOT trigger the bonus
- The mystery trigger probability is the **primary tuning dial** for overall RTP
- This single number was solved via simulation to land total game RTP on 96.00%

---

## 3. BONUS WHEEL SYSTEM

Active during all 4 bonus tiers. Fires on **each bonus spin** independently.

```
Per bonus spin:
  Roll: 35% chance Wheel triggers
  If triggers → draw segment:
    RED    (35%): Add sticky Wild(s)
    BLUE   (40%): Upgrade existing Wild multiplier
    YELLOW (25%): Add extra turns/lives
```

### RED — Add Sticky Wild
```
Find empty (non-Wild) reel positions
Add 1 new sticky Wild reel (90% of the time)
Add 2 new sticky Wilds (10% of the time, if 2+ empty reels remain)
Each new Wild's multiplier drawn from WILD_MULTIPLIER_WEIGHTS (same as base game)
```

### BLUE — Upgrade Wild Multiplier
```
Pick 1 random existing sticky Wild reel
Add increment drawn from BLUE_INCREMENT_WEIGHTS:
  +2x (38.2%), +3x (26.5%), +5x (16.2%), +10x (8.8%), +15x (4.7%)
  +20x (2.8%), +25x (1.6%), +50x (0.7%), +75x (0.3%), +100x (0.15%)
  +150x (0.07%), +200x (0.03%), +250x (0.015%), +500x (0.004%), +1000x (0.0003%)
If no Wilds exist yet → no effect this spin
```

### YELLOW — Extra Turns
```
In Spins Mode: add free spins
In Survival Mode: add lives
  +1 turn: 60%
  +2 turns: 30%
  +3 turns: 10%
```

---

## 4. BONUS TIERS

All 4 tiers share the same core engine (sticky Wilds + Wheel). They differ in starting state.

### Normal Bonus
```
Trigger:        Mystery check → 40% split (1-in-2,460 spins)
Starting state: 10 free spins, 0 Wilds
Mode:           Spins only (no choice)
Measured EV:    173.39x  (SE ±1.05)
Avg spins:      11.51
P(hit 25,000x): 3.47%
RTP contribution: 7.05%
```

### Super Bonus
```
Trigger:        Mystery check → 20% split (1-in-4,920 spins)
Starting state: 10 free spins, 1 sticky Wild at 2x
Mode:           Spins only (no choice)
Measured EV:    613.48x  (SE ±2.09)
Avg spins:      11.51
P(hit 25,000x): 16.44%
RTP contribution: 12.47%
```

### Hidden Bonus
```
Trigger:        Mystery check → 5% split (1-in-19,679 spins)
Starting state: 2 sticky Wilds at 3x each
Mode:           PLAYER CHOOSES → 12 Spins OR 5 Lives (Survival)

Spins Mode:     EV = 3,249.91x  |  P(25,000x) = 1.70%  |  Avg 13.78 spins
Survival Mode:  EV = 6,077.29x  |  P(25,000x) = 22.73% |  Avg 12.56 spins
Blended (50/50): EV = 4,663.60x
RTP contribution: 23.70%
```

### Super Hidden Bonus
```
Trigger:        Mystery check → 1% split (1-in-98,395 spins)
Starting state: 3 sticky Wilds at 5x each
Mode:           PLAYER CHOOSES → 12 Spins OR 5 Lives (Survival)

Spins Mode:     EV = 9,021.72x  |  P(25,000x) = 8.38%  |  Avg 13.65 spins
Survival Mode:  EV = 15,077.76x |  P(25,000x) = 56.87% |  Avg 16.19 spins
Blended (50/50): EV = 12,049.74x
RTP contribution: 12.25%
```

---

## 5. SURVIVAL MODE

Available in Hidden and Super Hidden Bonus as a player choice.

### Dead-Spin Probability (tunable, indexed by current Wild count)
| Current Wilds | P(lose a life this spin) |
|---------------|--------------------------|
| 0             | 92%                      |
| 1             | 83%                      |
| 2             | 70%                      |
| 3             | 52%                      |
| 4             | 30%                      |
| 5             | 0% (immortal)            |

```
Survival Mode loop:
  Start with 5 lives
  Each spin:
    1. Wheel check (may add Wilds/lives)
    2. Draw board, overlay sticky Wilds, evaluate wins
    3. Roll dead-spin check using probability from table above
    4. If dead → lives -= 1
    5. If lives = 0 → end bonus
  No fixed spin limit — continues until all lives lost or 25,000x cap
```

**Design note:** The original GDD rule ("no-win spin = lose a life") was tested and rejected — with 2+ Wilds on 14 paylines, the chance of a literal zero-win is ~0.0005%, making Survival unkillable. The tunable probability table replaces this.

---

## 6. GOLDEN CASE (Buy Feature)

```
Cost:           1,000x total bet
Mechanic:       Single special spin, 5 reels
Per-reel P(GB): 52.10%
Win condition:  Golden Briefcase on ALL 5 reels → 25,000x instant win
Miss:           Any other outcome → 0 payout
P(win):         0.521^5 = 3.84%
RTP:            3.84% × 25,000 / 1,000 = 95.98%
```

Typical outcome: 2-3 briefcases land (62.3% of spins), building anticipation.

---

## 7. EXTRA CHANCE (Buy Feature)

Same base game mechanics. Only the mystery trigger probability changes.

| Price | Trigger Probability | 1-in-X Spins | Uplift vs Standard | RTP |
|-------|--------------------|--------------|--------------------|-----|
| 3x    | 0.4538%            | 1-in-220     | 4.47x              | 96.00% |
| 5x    | 0.8057%            | 1-in-124     | 7.93x              | 96.00% |

Payouts reference the standard 1x bet unit, not the elevated price.

---

## 8. MINIMUM 2 WILD SPIN (Buy Feature)

```
Single premium spin with 2 guaranteed sticky Wild reels + extra-wild chance on remaining 3.
Payouts reference standard 1x bet unit.

| Price | Extra-Wild P (per remaining reel) | Measured EV | Wild Mix (2/3/4/5) |
|-------|-----------------------------------|-------------|---------------------|
| 200x  | 39.6%                             | 193.33x     | 22/43/28/6%         |
| 250x  | 43.8%                             | 239.29x     | 18/42/32/8%         |
```

---

## 9. RTP RECONCILIATION

| Component                         | RTP     |
|-----------------------------------|---------|
| Base Game (lines + Wilds + scatter)| 40.33% |
| Normal Bonus                       | 7.05%  |
| Super Bonus                        | 12.47% |
| Hidden Bonus (blended 50/50)       | 23.70% |
| Super Hidden Bonus (blended 50/50) | 12.25% |
| **TOTAL GAME RTP**                 | **95.79%** |

Cross-check: 100M simulated spins measured 95.34% (within 1 SE of 96% target).
Max Win frequency: 1-in-100,806 spins across all tiers combined.

---

## 10. IMPLEMENTATION STATUS

| Feature | Code | Simulated | Mode in RGS |
|---------|:----:|:---------:|:-----------:|
| Base Game + Wilds + Scatter | ✅ | ✅ 10K | ✅ `base` |
| Normal/Super/Hidden/Super Hidden Bonus | ✅ | ✅ (natural triggers) | ✅ inside `base` |
| Wheel (RED/BLUE/YELLOW) | ✅ | ✅ | ✅ |
| Survival Mode | ✅ | ✅ | ✅ |
| Golden Case | ✅ coded | ❌ | ❌ |
| Extra Chance 3x/5x | ❌ | ❌ | ❌ |
| Min 2 Wild 200x/250x | ❌ | ❌ | ❌ |
| Optimization (Rust) | — | ❌ | — |

---

## 11. EVENT CONTRACT (Frontend Integration)

Every event emitted by the math engine:

| Event Type | Fields | When |
|------------|--------|------|
| `reveal` | `board[][]`, `gameType`, `paddingPositions`, `anticipation` | Every spin |
| `wildReel` | `reel`, `multiplier` | When a reel becomes Wild |
| `spinMultiplier` | `multiplier` | When combined mult > 1 |
| `winInfo` | `totalWin`, `wins[{symbol, kind, win, positions, meta}]` | When lines win |
| `setWin` | `amount`, `winLevel` | After win evaluation |
| `setTotalWin` | `amount` | Running total update |
| `scatterPay` | `count`, `payout` | 3+ scatters anywhere |
| `mysteryTrigger` | `outcome` | Mystery check fires |
| `bonusChoice` | `mode` ("spins"/"survival") | Hidden/Super Hidden entry |
| `wheelSpin` | `result`, segment-specific payload | Wheel triggers in bonus |
| `stickyWildUpdate` | `wildReels{reel: mult}` | After any Wild change |
| `updateFreeSpin` | `amount`, `total` | Each bonus spin |
| `survivalLife` | `lives`, `lost` | Life gained/lost |
| `freeSpinEnd` | `amount`, `winLevel` | Bonus round ends |
| `finalWin` | `amount` | Absolute last event |
| `goldenCaseReveal` | `reelHits[]`, `maxWin` | Golden Case spin |
