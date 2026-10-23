# Vice Cartel — Frontend Integration (math v2.0)

Everything here matches the published books in `library/publish_files/`.
Real example rounds for every case are in [`sample_books/`](sample_books/) (see `sample_books/index.json`).
The new frontend config is [`config_fe_vice_cartel.json`](config_fe_vice_cartel.json).

All amounts in events are **× bet × 100** (integer). `250` = 2.5× bet. Max win `2500000` = 25,000×.

---

## 1. What changed from v1

| Area | v1 (old) | v2 (new) |
|---|---|---|
| Modes | `base`, `extra_chance_3x`, `extra_chance_5x`, `min2wild_200x`, `min2wild_250x`, `golden_case` | `base`, `extra_chance`, `bonus_normal`, `bonus_super`, `min2wild`, `golden_case` |
| Bonus trigger | Hidden "mystery" check (`mysteryTrigger` event) | **3–6 Scatters** on the board (`bonusTrigger` event) |
| Scatter | On the reel strip | **Not on the reel strip.** Placed on the board by the math (0–6 per spin) |
| Bonus buy | none | `bonus_normal` 100×, `bonus_super` 200× |
| Five Wild reels | Normal line win | **Instant 25,000× max win**, round ends (`fiveWilds`) |
| Wheel | RED / BLUE / YELLOW | RED / BLUE / YELLOW / **MAX_WIN** |
| RED | Adds Wild reels | Adds Wild reels, but **never more than 4 Wild reels** in total |
| BLUE with no Wild | (no event) | `wheelSpin` BLUE with no fields (nothing happens) |
| `updateFreeSpin` | Not reliable | Real counter: `amount` = current spin (1-based), `total` = total spins |
| RTP | 96.30% | 96.40% (Golden Case 96.30%) |

Removed events: `mysteryTrigger`.
New events: `bonusTrigger`, `bonusStart`, `fiveWilds`.

---

## 2. Bet modes

| Mode | Cost | Type in config | What the player gets |
|---|---|---|---|
| `base` | 1× | `feature: true` | Normal spin |
| `extra_chance` | 3× | `feature: true` (toggle, not a buy) | Normal spin, Scatters 3–6 are 5× more likely |
| `bonus_normal` | 100× | `buyBonus: true` | Normal Bonus straight away |
| `bonus_super` | 200× | `buyBonus: true` | Super Bonus straight away |
| `min2wild` | 100× | `buyBonus: true` | One spin with at least 2 Wild reels |
| `golden_case` | 1000× | `buyBonus: true` | M-A-X letter reveal, all 3 = 25,000× |

Max win is 25,000× in every mode.

---

## 3. Bonus tiers

Scatter count on the trigger spin picks the tier. Bonus buys start the tier directly.

| Scatters | Tier (`tier` field) | Spins | Starting Wild reels | Start multiplier each |
|---|---|---|---|---|
| 3 | `normal_bonus` | 10 | 0 | — |
| 4 | `super_bonus` | 10 | 1 | 2× |
| 5 | `hidden_bonus` | 12 | 2 | 3× |
| 6 | `super_hidden_bonus` | 12 | 3 | 5× |

Wild reels in the bonus are **sticky** for the whole bonus.
Before each bonus spin the Wheel may spin. Scatters never appear in bonus spins.

---

## 4. Event reference

| Event | Fields | When |
|---|---|---|
| `reveal` | `board[reel][row]`, `gameType` (`basegame`/`freegame`), `paddingPositions`, `anticipation` | Every spin. Wild reels show `{"name":"W","wild":true}` on all 4 rows. Scatters show as `SC` |
| `wildReel` | `reel`, `multiplier` | Base / Extra Chance / Min 2 Wild: one per Wild reel, **before** `reveal` |
| `spinMultiplier` | `multiplier` | Sum of all Wild reel multipliers, when > 1 |
| `winInfo` | `totalWin`, `wins[{symbol, kind, win, positions, meta}]` | Line wins (already multiplied). See §6 for `positions` |
| `setWin` | `amount`, `winLevel` | After a winning spin |
| `setTotalWin` | `amount` | Running round total |
| `scatterPay` | `count`, `payout` | 3+ Scatters: pays 3 = 0.5×, 4 = 2×, 5/6 = 5× |
| `bonusTrigger` | `tier`, `scatterCount` | Base / Extra Chance: bonus is triggered |
| `bonusStart` | `tier`, `spins`, `wildReels{reel: mult}` | Bonus begins (also first event of a bonus buy) |
| `updateFreeSpin` | `amount` (spin number, 1-based), `total` | Start of each bonus spin |
| `wheelSpin` | `result` + payload (below) | Wheel lands, before that spin's `reveal` |
| `stickyWildUpdate` | `wildReels{reel: mult}` | After every `wheelSpin` (except MAX_WIN). Full current sticky set |
| `fiveWilds` | `amount` (2500000) | Max win award: 5 Wild reels **or** Wheel MAX_WIN |
| `wincap` | `amount` | Round hit 25,000× |
| `freeSpinEnd` | `amount`, `winLevel` | Bonus ends. `amount` = bonus part only |
| `goldenCaseReveal` | `lettersLanded` (1–3), `maxWin` (bool) | Golden Case |
| `finalWin` | `amount` | Last event of every round. **This is the paid amount** |

### `wheelSpin` payloads

| `result` | Extra fields | Meaning |
|---|---|---|
| `RED` | `newWilds{reel: mult}` (1 or 2 reels) | New sticky Wild reels. Never above 4 Wild reels in total |
| `RED` | `newWilds{}` (empty) | Already 4 Wild reels: nothing added |
| `BLUE` | `reel`, `increment`, `newMult` | One sticky Wild's multiplier goes up |
| `BLUE` | *(none)* | No Wild reel yet: nothing happens |
| `YELLOW` | `extraTurns` (1–3) | Extra spins. Next `updateFreeSpin.total` is higher |
| `MAX_WIN` | *(none)* | 25,000× win. Followed by `fiveWilds`, `wincap`; bonus ends |

`wildReels` / `newWilds` keys are reel indexes as strings (`"0"`–`"4"`).

---

## 5. Round flows

**Base spin, no bonus** (`base_no_win`, `base_line_win`, `base_wild_multiplier_win`)
```
wildReel* → reveal → spinMultiplier? → winInfo? → setWin? → setTotalWin → finalWin
```

**Five Wild reels** (`base_five_wilds_max_win`, `min2wild_five_wilds_max_win`)
```
wildReel ×5 → reveal → fiveWilds → wincap → setTotalWin → finalWin(2500000)
```

**Base spin that triggers a bonus** (`base_bonus_*`, `extra_chance_bonus`)
```
reveal(3–6 SC) → [line win events] → setTotalWin → scatterPay → bonusTrigger → bonusStart
  per spin: updateFreeSpin → (wheelSpin → stickyWildUpdate)? → reveal → spinMultiplier? → winInfo? → setWin? → setTotalWin
→ freeSpinEnd → finalWin
```

**Bonus buy** (`bonus_normal_buy`, `bonus_super_buy`)
```
bonusStart → per spin (as above) → freeSpinEnd → finalWin
```
No base `reveal`, no `bonusTrigger`, no `scatterPay`.

**Wheel MAX_WIN** (`base_bonus_wheel_max_win`)
```
updateFreeSpin → wheelSpin(MAX_WIN) → fiveWilds → wincap → setTotalWin(2500000) → freeSpinEnd → finalWin(2500000)
```

**Max win reached by line wins in the bonus** (`base_bonus_wincap_by_wins`)
```
... reveal → winInfo → wincap → setTotalWin(2500000) → freeSpinEnd → finalWin(2500000)
```
Remaining spins are not played.

**Min 2 Wild** (`min2wild_win`): same as a base spin, always 2+ `wildReel` events. No Scatters, no bonus.

**Golden Case** (`golden_case_win`, `golden_case_lose`)
```
goldenCaseReveal → setWin? → setTotalWin → finalWin
```

---

## 6. Things to handle carefully

1. **Win positions are row + 1.** `winInfo.wins[].positions[].row` is 1 higher than the row in `reveal.board`
   (SDK default `include_padding_index`, while the board has no padding rows).
   Use `boardRow = position.row - 1`. Example in `base_line_win.json`: line 1 (top row, row 0) is reported as row 1.
   *Tell the math team if you want 0-based rows instead; that needs a book regeneration.*
2. **`finalWin` is the paid amount.** It can be up to 0.1× lower than the last `setTotalWin`,
   because the round is floored to 0.1× (e.g. `setTotalWin 17731` → `finalWin 17730`).
3. **Scatter pay is not in the `setTotalWin` before it.** On a trigger spin `setTotalWin` comes before `scatterPay`;
   add `scatterPay.payout` to the total yourself, or wait for the next `setTotalWin` (it includes it).
4. **`fiveWilds` means "max win awarded".** It follows both 5 Wild reels and the Wheel MAX_WIN. Check the preceding
   `wheelSpin` to pick the animation.
5. **The capping spin's `winInfo.totalWin` can exceed the cap.** Show the capped amount from `wincap` / `setTotalWin`.
6. **`freeSpinEnd.amount` is normally the bonus part only** (excludes the trigger spin's scatter/line win).
   When the bonus hits the cap through line wins it shows the full 2500000. Use it only for the bonus summary screen.
7. **Scatter is not on the reel strip.** `paddingReels` in the config has no `SC`; Scatters appear only in `reveal`
   boards (base / Extra Chance). Boards may show 1–2 Scatters without a bonus.
8. With 4 Wild reels on the trigger spin there is room for only 4 Scatters, so `scatterCount` is at most 4 then.

---

## 7. Config changes (`config_fe_vice_cartel.json`)

| Key | Change |
|---|---|
| `rtp` | 0.963 → 0.964 |
| `betModes` | Old 6 modes replaced by the 6 modes in §2. `extra_chance` is now `feature: true, buyBonus: false` (3× only; 5× removed). `min2wild` is one mode at 100× (200×/250× removed). New `bonus_normal`, `bonus_super` |
| `paddingReels` | Strip is 182 stops (was 191): `SC` removed. Same strip for `basegame` and `freegame` |
| `symbols` | Same symbols and paytable (`SC` still listed as scatter, no line pay) |
| `paylines`, `numReels`, `numRows` | Unchanged (14 lines, 5×4) |

---

## 8. Sample books

| File | Shows |
|---|---|
| `base_no_win` | Zero win |
| `base_line_win` | Line win, no Wilds |
| `base_wild_multiplier_win` | Wild reel + `spinMultiplier` |
| `base_five_wilds_max_win` | 5 Wild reels → 25,000× |
| `base_bonus_normal` / `_super` / `_hidden` / `_super_hidden` | Each bonus tier from Scatters |
| `base_bonus_wheel_red` / `_blue` / `_blue_no_wild` / `_yellow` / `_max_win` | Each Wheel result |
| `base_bonus_wincap_by_wins` | Bonus reaching 25,000× by wins |
| `extra_chance_bonus` | Extra Chance round with a bonus |
| `bonus_normal_buy` / `bonus_super_buy` | Bonus buys |
| `min2wild_win` / `min2wild_five_wilds_max_win` | Min 2 Wild |
| `golden_case_win` / `golden_case_lose` | Golden Case |

Some files are the same round (one round can show several Wheel results). Regenerate with
`python games/vice_cartel/frontend/extract_sample_books.py` after a new book run.
