# Vice Cartel — Game Math Audit (code-first)

**Audit date:** 2026-10-23
**Code audited:** `stake-math-sdk-vicecartel` at commit `798f3b5` (working tree clean). The game's Python files were last changed in `af15c70` (2026-10-12 00:17 +0530). The published artifacts in `games/vice_cartel/library/` were written between 00:19 and 00:57 on 2026-10-12, so **they match the current code**.
**Scope:** everything under `games/vice_cartel/` plus the SDK modules it executes (`src/`, `optimization_program/`, `utils/rgs_verification.py`, `utils/analysis/`).
**Constraint followed:** no simulations or RTP test runs were performed. Every number in this report is one of:

| Label               | Meaning                                                                                                                                                         |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CONFIGURED**      | Literal value in source code / config                                                                                                                           |
| **DERIVED (exact)** | Computed analytically from configured values by exhaustive enumeration or closed form, no randomness                                                            |
| **ARTIFACT**        | Read from existing generated files (`library/stats_summary.json`, `library/statistics_summary.json`, `library/configs/*.json`, lookup tables). Not re-computed. |
| **COMMENT**         | A number that appears only in a code comment; its derivation is not in the repository                                                                           |
| **UNVERIFIED**      | Could not be established from code + exact analysis; see §14                                                                                                    |

All file paths are relative to `stake-math-sdk-vicecartel/`.

---

## 1. Executive summary

1. **Six bet modes exist:** `base` (1x), `extra_chance_3x` (3x), `extra_chance_5x` (5x), `min2wild_200x` (200x), `min2wild_250x` (250x), `golden_case (mwon)` (1000x). . Vice Cartel's max-win-or-nothing mechanic is `golden_case` (§7.1).
2. **The board is not a reel window.** Each of the 20 cells is drawn independently and uniformly from a 191-stop strip with no Wilds (`game_executables.py:15-25`). Every reel has the same symbol counts. Wilds never come from the strip. A whole reel is overwritten with `W` by a separate Bernoulli roll (4.5% per reel in base play).
3. **The multiplier is the sum of all Wild-reel multipliers** (or 1 if there are none). It multiplies the total line win and never the scatter pay.
4. **The bonus is never rolled during a spin.** Bonus rounds exist only in books generated under the `freegame` criteria, where a bonus is forced. How often players see one is set entirely by the optimizer's lookup-table weights (target 1 in 1,455.48 spins in `base`). `MYSTERY_TRIGGER_PROB`\*, `BASE_ONLY_RTP` and `BASE_HIT_RATE` are consumed **only by the optimizer** (`game_optimization.py`), never by game logic.
5. `base`**,** `extra_chance_3x` **and** `extra_chance_5x` **publish byte-identical books.** The three book files share sha256 `27f1da5d…5355` (`library/configs/config.json`), and the unweighted lookup tables also hash identically. The modes differ **only** in optimizer weights. Extra Chance changes no reel, symbol, Wild or bonus probability inside a round.
6. **Exact base-game RTP before 0.1x flooring is 40.5806%** (DERIVED, exact). This matches the `0.4058` in the `BASE_ONLY_RTP` comment. The 1.34% flooring loss and the 1-in-3.44 hit rate are measured values that could not be verified analytically.
7. **The natural uncapped bonus EV is 899.33x per bonus** (DERIVED, exact Markov chain). That is 899.73x per bonus book including the triggering base spin. The optimizer forces the bonus fence average to **830.50x**. The gap must be closed by the 25,000x cap, the 0.1x flooring and/or optimizer reweighting of bonus books. Which share each contributes is **UNVERIFIED** without a capped analysis or reading the unweighted books.
8. **Golden Case theoretical RTP is 96.30004%** (P(win) = 3.852002%, 1 in 25.96). Its books are published **unweighted**, so the deployed RTP is the sample value **96.49%** (ARTIFACT: 38,597 wins in 1,000,000 books).
9. **Min 2 Wild uncapped exact RTP is 96.628% (200x) and 96.581% (250x)**, not the 96.35% stated in the config comment. With exact cap losses for 4–5 Wild boards and upper bounds for the rest, the capped and floored RTP lies in [95.73%, 96.51%] and [95.88%, 96.45%]. The published unweighted samples are 96.32% and 96.33% (ARTIFACT).
10. **All modes share a 25,000x round cap.** Uncapped, a single base spin can reach 420,000x (five 1000x Wild reels × 84x line win).
11. **Several existing documents are stale or wrong** (`check.md`, `test.md`, `report.md`, `Math Distribution & Summary.txt`, and parts of `VICE_CARTEL_TECHNICAL_SPEC.md`). See §14.

---

## 2. Scope and methodology

1. **Inventory.** Read every file in `games/vice_cartel/`, plus the SDK modules on the execution path: `src/state/state.py`, `src/state/run_sims.py`, `src/state/books.py`, `src/executables/executables.py`, `src/calculations/lines.py`, `src/calculations/statistics.py`, `src/calculations/symbol.py`, `src/wins/win_manager.py`, `src/wins/multiplier_strategy.py`, `src/config/*.py`, `src/events/events.py`, `optimization_program/optimization_config.py`, `optimization_program/run_script.py`, `optimization_program/src/main.rs` (fence parsing), `utils/rgs_verification.py`, `utils/analysis/distribution_functions.py`.
2. **Active SDK copy.** The venv uses an editable install. `env/Lib/site-packages/__editable___stakeengine_0_0_0_finder.py` maps `src`, `optimization_program` and `utils` to the repository folders, so `env/src/stakeengine/` (a second SDK copy) is **not** used. Since upstream commit `4f3942a`, only `optimization_program/src/setup.toml` (run parameters) and `utils/analysis/distribution_functions.py:211-212` (a guard for 2-value distributions) were changed in SDK code.
3. **Execution trace.** Followed `run.py` → `create_books` → `GameState.run_spin` → executables → `Lines.get_lines` → `WinManager` → `evaluate_finalwin` → `Book.to_json` → lookup tables → optimizer → `generate_configs`.
4. **Exact analysis** (no simulation). A read-only Python script imported `GameConfig` and the SDK, then:
   - re-implemented the single-line evaluator and **cross-checked it against** `Lines.get_lines` **on 30,000 random boards: 0 mismatches**;
   - enumerated every symbol combination on one payline (9⁵ = 59,049 combinations) for each of the 32 possible Wild-reel subsets, in exact rational arithmetic;
   - computed scatter-count distributions by exact convolution;
   - solved the bonus as a Markov chain over (Wild-reel set, turns left) with linear propagation of the expected multiplier sum (§10.6);
   - evaluated Golden Case in closed form.

   The script was kept outside the repository because the brief said no RTP tests.

5. **Artifacts** were read, not regenerated.

---

## 3. Architecture and execution flow

### 3.1 Offline pipeline (`games/vice_cartel/run.py`)

| Step | Code                                           | Behaviour                                                                     |
| ---- | ---------------------------------------------- | ----------------------------------------------------------------------------- |
| 1    | `run.py:15-19`                                 | `num_threads=10`, `rust_threads=20`, `batching_size=5000`, `compression=True` |
| 2    | `run.py:21-28`                                 | 1,000,000 books per mode, all 6 modes                                         |
| 3    | `run.py:45-50`                                 | Deletes old `publish_files/lookUpTable_<mode>_0.csv`                          |
| 4    | `run.py:52-60` → `src/state/run_sims.py:15-80` | Simulates books                                                               |
| 5    | `run.py:62`                                    | `generate_configs` (writes `math_config.json`, `config.json`, `index.json`)   |
| 6    | `run.py:37,64-66`                              | Rust optimizer **only for** `base`, `extra_chance_3x`, `extra_chance_5x`      |
| 7    | `run.py:68-72`                                 | Stats sheet + RGS format checks                                               |

**Criteria assignment.** `get_sim_splits` (`run_sims.py:83-98`) gives each criteria `int(num_sims × quota)` books, using `random.seed(0)`. `assign_sim_criteria` (`run_sims.py:101-105`) shuffles them.

**Seeding.** `GameState.run_spin` calls `self.reset_seed(sim)` (`gamestate.py:20`), which runs `random.seed(sim + 1)` (`src/state/state.py:88-94`). The `simulation_seed` argument is **ignored**. Repeats inside one book continue the same Mersenne-Twister stream. Because the criteria assignment and seeds depend only on the sim index and the quotas, modes with identical distributions and code paths produce identical books (see Executive summary item 5).

### 3.2 One book (`GameState.run_spin`, `gamestate.py:19-52`)

```
reset_seed(sim)
repeat:
    reset_book()                                   # game_override.py:9-13 + state.py:66-86
    if betmode == "golden_case":  run_golden_case(); evaluate_finalwin(); stop     # :25-29
    if betmode in {min2wild_200x, min2wild_250x}:                                  # :31-38
        draw_min2wild_board(p_extra); evaluate_lines_with_wilds(); evaluate_scatter_pay()
        update_gametype_wins(); evaluate_finalwin(); stop
    draw_wild_board(); evaluate_lines_with_wilds(); evaluate_scatter_pay()        # :40-43
    update_gametype_wins(basegame)
    if criteria.force_freegame:  triggered_freegame=True; run_bonus(random tier)  # :46-48
    evaluate_finalwin()                                                            # 0.1x floor, then cap
    check_repeat()                                                                 # accept/reject vs criteria
imprint_wins()                                                                     # book → library
```

`check_repeat` (`game_override.py:30-40`) rejects and redraws a book if its criteria has `win_criteria` and `final_win != win_criteria` (criteria `"0"` requires exactly 0), or if `force_freegame` is set but no bonus ran (cannot happen, because the bonus is forced). Golden Case and Min 2 Wild `break` before `check_repeat`, so they never repeat.

### 3.3 Production (outside this repository)

The RGS does **not** run this Python code. It serves a pre-generated book chosen from `lookUpTable_<mode>_0.csv`, whose rows are `book_id, weight, payoutMultiplier×100`. The RGS selection algorithm is not in this repository. By Stake Engine convention, book _i_ is selected with probability weight*ᵢ*/Σweight. Under that convention, the deployed RTP of a mode is **exactly** the weighted mean payout of its lookup table divided by its cost (`utils/analysis/distribution_functions.py:197-201`), not the theoretical value of the generator. RGS-side selection is **UNVERIFIED** from local code.

---

## 4. Inventory of math-related files

| File                                                                                                        | Role                                                                        | Status                      |
| ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | --------------------------- |
| `games/vice_cartel/game_config.py`                                                                          | All probability tables, paytable, paylines, reels, bet modes, distributions | Active                      |
| `games/vice_cartel/reels/BR0.csv`                                                                           | Single 191-stop × 5-column strip set                                        | Active                      |
| `games/vice_cartel/game_calculations.py`                                                                    | Bernoulli/weighted draws, scatter counting, Golden Case letters             | Active                      |
| `games/vice_cartel/game_executables.py`                                                                     | Board drawing, line/scatter evaluation, wheel, bonus spin, Golden Case      | Active                      |
| `games/vice_cartel/game_override.py`                                                                        | Bonus tier table, 0.1x flooring, repeat rule                                | Active                      |
| `games/vice_cartel/gamestate.py`                                                                            | Mode routing, bonus loop, forced mystery tier                               | Active                      |
| `games/vice_cartel/game_events.py`                                                                          | Frontend events (no math)                                                   | Active                      |
| `games/vice_cartel/game_optimization.py`                                                                    | Optimizer fence targets                                                     | Active (offline only)       |
| `games/vice_cartel/run.py`                                                                                  | Pipeline                                                                    | Active (offline only)       |
| `src/calculations/lines.py` `get_lines`                                                                     | Payline evaluation                                                          | Active                      |
| `src/calculations/statistics.py` `get_random_outcome`                                                       | Weighted draw                                                               | Active                      |
| `src/wins/multiplier_strategy.py`                                                                           | Per-line symbol multiplier (always 1 here, §5.6)                            | Active, effectively a no-op |
| `src/wins/win_manager.py`, `src/state/state.py`, `src/executables/executables.py`                           | Win accounting, final win, cap                                              | Active                      |
| `src/state/run_sims.py`, `src/state/books.py`, `src/write_data/*`                                           | Book generation and output                                                  | Active (offline)            |
| `optimization_program/*`                                                                                    | Rust weight optimizer                                                       | Active (offline)            |
| `utils/rgs_verification.py`                                                                                 | Lookup/book format checks, mode stats                                       | Active (offline)            |
| `GameState.run_freespin` (`gamestate.py:71-72`)                                                             | `pass`                                                                      | Dead                        |
| `config.freespin_triggers`, `anticipation_triggers` (`game_config.py:115-122`)                              | Empty / 0                                                                   | Unused                      |
| `GameCalculations.evaluate_lines(global_multiplier)`                                                        | Parameter never passed                                                      | Unused                      |
| `MYSTERY_OUTCOME_WEIGHTS["no_bonus"]`                                                                       | Only used to compute `_BONUS_SHARE`                                         | No runtime effect           |
| `tests/win_calculations/*`                                                                                  | Generic SDK tests; **no Vice-Cartel-specific tests exist**                  | Not game-specific           |
| `env/src/stakeengine/`                                                                                      | Second SDK copy                                                             | Not imported                |
| `check.md`, `test.md`, `report.md`, `Math Distribution & Summary.txt`, `games/vice_cartel/VICE_CARTEL_*.md` | Earlier documentation                                                       | See §14                     |

---

## 5. Base game (`base`, cost 1x)

### 5.1 Grid

5 reels × 4 rows (`game_config.py:74-75`). 14 fixed paylines (§9.3). `include_padding = False` (`:110`).

### 5.2 Reel strip and symbol probabilities

`self.reels = {"BR0": read_reels_csv("BR0.csv")}` (`game_config.py:125-127`). The CSV has 191 rows and 5 columns, and column _r_ is the strip for reel _r_. The symbol **order differs** between columns, but the **counts are identical** (DERIVED from the CSV):

| Symbol    | Stops per reel | P(cell = symbol \| reel not Wild) = n/191 | Marginal P(cell) in base play = 0.955·n/191 |
| --------- | -------------- | ----------------------------------------- | ------------------------------------------- |
| H1        | 3              | 1.5707%                                   | 1.50%                                       |
| H2        | 6              | 3.1414%                                   | 3.00%                                       |
| H3        | 10             | 5.2356%                                   | 5.00%                                       |
| H4        | 16             | 8.3770%                                   | 8.00%                                       |
| L1        | 24             | 12.5654%                                  | 12.00%                                      |
| L2        | 32             | 16.7539%                                  | 16.00%                                      |
| L3        | 41             | 21.4660%                                  | 20.50%                                      |
| L4        | 50             | 26.1780%                                  | 25.00%                                      |
| SC        | 9              | 4.7120%                                   | 4.50%                                       |
| W         | 0              | 0                                         | 4.50% (whole-reel event)                    |
| **Total** | **191**        | 100%                                      | 100%                                        |

Note that 0.955/191 = 0.005 exactly, so each strip stop is worth exactly 0.5% of marginal probability in base play. This reproduces the original 200-stop design (191 normal + 9 W) described in `test.md`. However, the Wild is a whole-reel event: the 4 cells of a reel are perfectly correlated for W and independent otherwise. The marginal column is therefore **not** a valid basis for computing line probabilities. Use the conditional column together with the Wild-reel distribution.

**Selection algorithm** (`game_executables.py:15-25`): for every reel and every row, `strip[random.randrange(191)]`. That is 20 independent uniform draws with replacement. The stop index is not reused across rows, and `reel_positions` is set to `[0]*5`. Every row of a reel therefore has the same distribution, and all 20 cells are mutually independent.

### 5.3 Full-reel Wilds

`draw_wild_board` (`game_executables.py:27-38`): for each reel, `random.random() < PER_REEL_WILD_PROB` (0.045, `game_config.py:43`; `game_calculations.py:17-18`). On success the reel's multiplier is drawn from `WILD_MULTIPLIER_WEIGHTS` and all 4 cells are replaced with `W`.

Number of Wild reels _K_ ~ Binomial(5, 0.045) (DERIVED):

| K   | P(K)          | 1 in      |
| --- | ------------- | --------- |
| 0   | 79.4359%      | 1.26      |
| 1   | 18.7153%      | 5.34      |
| 2   | 1.76374%      | 56.7      |
| 3   | 0.0831083%    | 1,203     |
| 4   | 0.00195805%   | 51,071    |
| 5   | 0.0000184528% | 5,419,228 |

### 5.4 Wild multiplier and spin multiplier

`WILD_MULTIPLIER_WEIGHTS` (`game_config.py:11-15`), drawn by `get_random_outcome` (`src/calculations/statistics.py:5-17`). That function draws `roll = uniform(0, Σw)` and returns the first value whose cumulative weight ≥ roll, so **P(v) = w_v / Σw**. Total weight is 8,874.32. Full table in §9.4. **Mean μ_W = 4.171587**, E[m²] = 100.8190, SD = 9.1333.

Spin multiplier: `compute_spin_multiplier` (`game_calculations.py:25-26`) returns `sum(wild_reels.values())` if any Wild reel exists, else 1. Given _K_ = k ≥ 1, E[M] = k·μ_W. A single Wild reel with multiplier 1 gives M = 1 (probability 33.81% given K = 1).

### 5.5 Line evaluation (`src/calculations/lines.py:28-126`)

For each of the 14 lines:

- Read left to right. Leading `W`s count as `wild_matches`. The first non-W symbol becomes the line symbol. Further cells match if they equal it or are `W`. The run stops at the first non-match.
- `base_win = paytable[(wild_matches + matches, symbol)]` if that key exists. `wild_win = paytable[(wild_matches, "W")]`, which exists only for 5 W. The larger of the two is paid.
- Consequences (verified by enumeration):
  - A line of 5 W pays (5,"W") = 6.0.
  - 4 W plus any paying symbol X pays as 5-of-a-kind X. For example, W W W W L4 pays 0.4, not 6.0.
  - **SC never pays on a line and breaks it.** A line whose first non-W symbol is SC pays 0, even with leading Wilds (for example, W W W W SC pays 0).
- Paytable values are multiples of the **total bet**. There is no per-line bet division.

Then, in `evaluate_lines_with_wilds` (`game_executables.py:56-73`): `boosted = round(raw_total × M, 2)`, and each line win is also rounded to 2 decimals. The **spin multiplier is applied once to the summed line win**.

### 5.6 Per-line symbol multipliers: none

`get_lines` defaults to `multiplier_method="symbol"`, which sums the `multiplier` attribute of winning-position symbols (`multiplier_strategy.py:32-41`). `W` is defined only with the `wild` flag (`game_config.py:111`), so `Symbol.multiplier` stays `None` and the factor is always 1. The force files confirm this: `"mult": ["1"]` is the only value (`library/forces/force.json`).

### 5.7 Scatter pay

`evaluate_scatter_pay` (`game_executables.py:75-80`) counts `SC` on the final board, **after** Wild overwrite. It pays `scatter_pay = {3: 0.5, 4: 2.0, 5: 5.0}` (`game_config.py:113`), with counts of 5 or more paying 5.0 (`game_calculations.py:42-45`). Scatter pay is **not** multiplied by M, does **not** trigger anything, and is added to the base-game spin win.

Scatter-count distribution with no Wild reels (20 Bernoulli(9/191) cells, DERIVED):

| SC count | 0        | 1        | 2        | 3       | 4       | 5        | 6+       |
| -------- | -------- | -------- | -------- | ------- | ------- | -------- | -------- |
| P        | 38.0856% | 37.6670% | 17.6952% | 5.2502% | 1.1034% | 0.17461% | 0.02390% |

### 5.8 Base-game RTP (DERIVED, exact; before 0.1x flooring, uncapped)

Because the Wild-reel set _S_, the multiplier draws and the symbol draws are mutually independent, and every line has the same per-line EV given _S_ (all cells of a reel share one distribution):

\[
\text{RTP}_{\text{base}} = \sum_{S\subseteq\{0..4\}} 0.045^{|S|}\,0.955^{5-|S|}\Big[\,14\,\ell(S)\,\bar M(S) + \sigma(S)\Big],\qquad \bar M(\emptyset)=1,\ \bar M(S)=|S|\,\mu_W
\]

Here ℓ(S) is the exact single-line EV given Wild reels S (§10.3), and σ(S) is the exact scatter EV given the non-Wild reels.

| K Wild reels | P(K)       | Line contribution | Scatter contribution |
| ------------ | ---------- | ----------------- | -------------------- |
| 0            | 0.794359   | 0.036931          | 0.046267             |
| 1            | 0.187153   | 0.147063          | 0.005422             |
| 2            | 0.017637   | 0.130253          | 0.000202             |
| 3            | 0.000831   | 0.035005          | 0.0000024            |
| 4            | 0.0000196  | 0.004337          | ≈0                   |
| 5            | 0.00000018 | 0.000323          | 0                    |
| **Total**    | 1          | **0.353912**      | **0.051894**         |

**Base-game RTP before flooring = 0.405806 (40.5806%).** This matches the comment in `game_config.py:33` ("0.4058 exact"). About 89.6% of line RTP comes from spins with at least one Wild reel.

After 0.1x flooring (§12.2) the code comment states 0.3924, so the flooring loss is 0.0134 (COMMENT, measured). This needs the full win distribution and is **UNVERIFIED**. `BASE_HIT_RATE = 3.44` (1 in 3.44 spins pays ≥ 0.1x after flooring) is also a measured COMMENT and **UNVERIFIED**. The ARTIFACT base-mode `non_zero_hr` is 3.432 (including bonus books), which is consistent.

### 5.9 Bet and stake

`config.json` reports `betDenomination: 1000` and `minDenomination: 10` (`Config.min_denomination = 0.1`, `src/config/config.py:25`). Payouts are stored as `int(round(payout × 100))` (`src/state/books.py:31`) and must be multiples of 10, i.e. 0.1x (`utils/rgs_verification.py:117`). Bet-level templates (min/max bet) are RGS-side and not defined in this repository (**UNVERIFIED** here; see `rules.md`).

---

## 6. Bonus game (inside `base`, `extra_chance_3x`, `extra_chance_5x`)

### 6.1 Entry (the "mystery trigger")

There is **no in-spin trigger**. In `run_spin`, a bonus runs only when the book's criteria conditions have `force_freegame=True` (`gamestate.py:46-48`). That is true only for the `freegame` criteria (`game_config.py:142,146`). The tier is then drawn by `_forced_mystery_outcome` (`gamestate.py:74-78`) from `MYSTERY_OUTCOME_WEIGHTS` **with** `no_bonus` **removed** (`gamestate.py:8`):

| Tier               | Weight | P(tier \| bonus) | Base-mode frequency at target hr 1,455.48 |
| ------------------ | ------ | ---------------- | ----------------------------------------- |
| normal_bonus       | 40     | 60.606%          | 1 in 2,401.5                              |
| super_bonus        | 20     | 30.303%          | 1 in 4,803.1                              |
| hidden_bonus       | 5      | 7.576%           | 1 in 19,212                               |
| super_hidden_bonus | 1      | 1.515%           | 1 in 96,062                               |
| (no_bonus)         | 34     | never produced   | —                                         |

The tier frequencies in the last column assume the optimizer keeps the natural tier mix inside the bonus fence. The optimizer does not constrain tier mix (§11), so this is **UNVERIFIED** for the deployed tables.

The triggering spin is a full normal base spin (Wild reels, lines, scatter), and its win is included in the book.

### 6.2 Bonus initialisation (`game_override.py:42-57`)

| Tier               | Spins | Starting sticky Wild reels | Each starting multiplier | Starting M   |
| ------------------ | ----- | -------------------------- | ------------------------ | ------------ |
| normal_bonus       | 10    | 0                          | —                        | 1 (no Wilds) |
| super_bonus        | 10    | 1                          | 2                        | 2            |
| hidden_bonus       | 12    | 2                          | 3                        | 6            |
| super_hidden_bonus | 12    | 3                          | 5                        | 15           |

Starting reels are a uniform random subset (`random.sample(range(5), k)`). Starting multipliers are fixed, not drawn.

### 6.3 Per-spin loop (`gamestate.py:54-69`)

```
while turns_left > 0 and not wincap_triggered and spin_count < 200:
    spin_count += 1
    resolve_wheel()          # may add Wilds, add to a multiplier, or add turns
    run_bonus_spin()         # independent board, sticky reels = W, lines × M, NO scatter pay
    turns_left -= 1
```

- **No random Wild reels in the bonus.** Only sticky Wilds appear.
- **No scatter pay in the bonus.** `run_bonus_spin` (`game_executables.py:106-127`) never calls `evaluate_scatter_pay`.
- **No retrigger** of the bonus. YELLOW extends turns only.
- M is the sum of the sticky Wild multipliers, or 1 if there are none.
- Termination: turns exhausted, the 25,000x cap reached (`evaluate_wincap`, `src/executables/executables.py:35-41`, checked only after a positive line win), or 200 spins. The 200-spin cap is effectively unreachable: the probability mass remaining after 200 spins is about 10⁻⁵⁶ (DERIVED).

### 6.4 Wheel (`game_executables.py:82-104`, `game_calculations.py:48-65`)

Each bonus spin: `random() < 0.35` → segment by weights RED 35 / BLUE 40 / YELLOW 25 (total 100).

| Event per bonus spin | Probability          |
| -------------------- | -------------------- |
| No wheel             | 0.6500               |
| RED                  | 0.35 × 0.35 = 0.1225 |
| BLUE                 | 0.35 × 0.40 = 0.1400 |
| YELLOW               | 0.35 × 0.25 = 0.0875 |

- **RED:** add 2 Wilds with probability 0.10 (`RED_DOUBLE_WILD_PROB`), otherwise 1, capped at the number of empty reels. Reels are chosen uniformly among non-Wild reels, and each new Wild draws its own multiplier from `WILD_MULTIPLIER_WEIGHTS` (mean 4.171587). With all 5 reels Wild, RED does nothing.
- **BLUE:** if any sticky Wild exists, pick one uniformly and add an increment from `BLUE_INCREMENT_WEIGHTS` (total 6,803.32, **mean 5.845675**). With no sticky Wilds, BLUE does nothing, and only `stickyWildUpdate` is emitted, with no `wheelSpin` event.
- **YELLOW:** add 1/2/3 turns with weights 60/30/10 (mean 1.5).

**Expected spins.** Each spin adds 0.35 × 0.25 × 1.5 = 0.13125 expected turns. That gives E[spins] = N / (1 − 0.13125) = N / 0.86875: **11.5108** for 10-spin tiers and **13.8129** for 12-spin tiers (DERIVED; matches the Markov-chain output; ignores early termination by the cap).

### 6.5 Bonus EV (DERIVED, exact Markov chain; **uncapped, before flooring**)

Method in §10.6.

| Tier                            | E[spins] | Natural uncapped EV (x bet) | Final Wild-reel count distribution (0/1/2/3/4/5) |
| ------------------------------- | -------- | --------------------------- | ------------------------------------------------ |
| normal_bonus                    | 11.511   | **257.44**                  | 22.2 / 32.2 / 24.8 / 13.2 / 5.3 / 2.3 %          |
| super_bonus                     | 11.511   | **842.93**                  | — / 22.2 / 32.2 / 24.8 / 13.2 / 7.7 %            |
| hidden_bonus                    | 13.813   | **4,167.17**                | — / — / 16.4 / 28.6 / 26.2 / 28.8 %              |
| super_hidden_bonus              | 13.813   | **11,363.70**               | — / — / — / 16.4 / 28.6 / 55.0 %                 |
| **Tier-weighted (40/20/5/1)**   | —        | **899.33**                  |                                                  |
| + triggering base spin (0.4058) | —        | **899.73 per bonus book**   |                                                  |

The **optimizer target** for the bonus fence average is **830.50x** in `base` (830.44x and 830.43x in Extra Chance), computed as hr × rtp × cost (§11). The comment in `game_config.py:31` says "548.1x EV per mystery check", and 548.1 / 0.66 = 830.45.

The uncapped natural mean exceeds this target by 69.2x (+8.3%). The super_hidden mean of 11,364x lies close to the 25,000x cap, so the cap removes a large but **unquantified** amount, especially from the hidden tiers. Whether the natural **capped and floored** mean equals 830.5x is **UNVERIFIED**. If it does not, the optimizer distorts the bonus payout distribution (and therefore the effective tier mix) to hit 830.5x.

### 6.6 Bonus RTP contribution

| Mode            | Bonus fence rtp (configured target, relative to cost) |
| --------------- | ----------------------------------------------------- |
| base            | 0.5706                                                |
| extra_chance_3x | 0.8322                                                |
| extra_chance_5x | 0.88452                                               |

For reference only, the natural uncapped tier contributions at the base-mode target frequency are 0.1072 (normal) + 0.1755 (super) + 0.2169 (hidden) + 0.1183 (super hidden) = **0.6179**. That exceeds the 0.5706 target and is an upper bound, not a deployed figure.

---

## 7. MWON and other special modes

### 7.1 Golden Case (`golden_case`, cost 1000x): Vice Cartel's max-win-or-nothing mode

No MWON identifier exists anywhere under `stake-math-sdk-vicecartel/` (grep for `mwon` finds nothing). The workspace's MWON lives in `engine-clockwork` (Clockwork Heist, `GameMode.MWON`, `engine-clockwork/src/game/constants.ts:15,23`) and does not share code or config with Vice Cartel. It is out of scope.

Golden Case is the only Vice Cartel mode with a max-win-or-nothing structure:

- `run_spin` → `run_golden_case` (`gamestate.py:25-29`, `game_executables.py:129-136`). No board, no reels, no lines.
- `golden_case_spin` (`game_calculations.py:68-74`): roll 3 independent Bernoulli(q = 0.291759) letters (`GOLDEN_CASE_LETTER_PROB`, `game_config.py:45`). If 0 letters land, **re-roll the whole triple**. This is rejection sampling, which equals conditioning on at least 1 letter.
- 3 letters pays `wincap` (25,000x). 1 or 2 letters pay 0.
- Distribution: single criteria `golden_case`, quota 1.0 (`game_config.py:163-174`). **Not optimized** (`run.py:37`). Published with weight 1 per book (ARTIFACT: `lookUpTable_golden_case_0.csv` rows `id,1,payout`).

Exact math (DERIVED):

\[
P(n) = \frac{\binom{3}{n} q^n (1-q)^{3-n}}{1-(1-q)^3},\quad 1-(1-q)^3 = 0.644737
\]

| Letters         | P                           |
| --------------- | --------------------------- |
| 1               | 68.0960%                    |
| 2               | 28.0520%                    |
| 3 (win 25,000x) | **3.852002%** (1 in 25.961) |

- RTP = 25,000 × 0.03852002 / 1000 = **96.30004%**
- SD per buy = 25,000 × √(p(1−p)) = 4,811.2x, i.e. 4.811 per unit cost (ARTIFACT: 4.82)
- Expected re-rolls per buy = 0.551 (no payout effect)
- ARTIFACT (published, unweighted 1M books): 38,597 wins, average 964.925x, **RTP 96.49%** (hr 25.909). The sampling SD of a 1M-book RTP estimate is 25·√(p(1−p)/10⁶) = ±0.48%, so the deviation is +0.4σ. Because books are unweighted, **the deployed RTP is the sample's 96.49%**, not 96.30%.

### 7.2 Mystery trigger

See §6.1. It is not a mode. It exists only as optimizer fence targets.

---

## 8. Buy modes

All buy modes have `is_buybonus=True`, `max_win=25,000`, `rtp=0.963` and `auto_close_disabled=False` (`game_config.py:163-218`). Payouts are always in multiples of the **base bet**, and the RTP denominator is the mode cost (`distribution_functions.py:197-201`; `run_sims` thread RTP print, `state.py:269-277`).

### 8.1 Extra Chance (`extra_chance_3x` cost 3x, `extra_chance_5x` cost 5x)

- Code path: identical to `base` (`gamestate.py:40-51`), with the same `feature_distributions` (`game_config.py:145-149,183,193`).
- **Books: byte-identical to** `base`**.** sha256 `27f1da5d…5355` for all three `books_*.jsonl.zst`, and identical unweighted lookup tables (sha256 `52874A80…6E5F`).
- **No change** to strips, symbol probabilities, Wild probability, multipliers, bonus tiers or the wheel.
- The **only** difference is the optimizer fence targets (`game_optimization.py:39-57,66-69`):

| Mode            | Cost | Configured mystery P (`game_config.py:35-37`) | = (0.963·cost − 0.3924)/548.1 (DERIVED) | Bonus share 0.66 | Bonus fence hr | Bonus fence rtp | Base fence rtp = 0.3924/cost | Zero fence prob |
| --------------- | ---- | --------------------------------------------- | --------------------------------------- | ---------------- | -------------- | --------------- | ---------------------------- | --------------- |
| base            | 1    | 0.001041                                      | 0.0010411                               | ✓                | 1,455.48       | 0.5706          | 0.3924                       | 0.708615        |
| extra_chance_3x | 3    | 0.004555                                      | 0.0045550                               | ✓                | 332.63         | 0.8322          | 0.1308                       | 0.706296        |
| extra_chance_5x | 5    | 0.008069                                      | 0.0080690                               | ✓                | 187.77         | 0.88452         | 0.07848                      | 0.703977        |

Each mode's average non-zero base win is 3.44 × 0.3924 = 1.3499x of base bet, and its average bonus book is about 830.4–830.5x of base bet.

- Since 0.3924 + P_bonus × 830.45 = 0.963 × cost, all three modes reach 96.30% **by construction**. The bonus frequency is exactly what makes up the difference.
- Within-fence payout distributions **differ by mode** because each optimization run is independent. ARTIFACT evidence: the max-win frequency (`hr_max`) is 1 in 892.6M (base), 1 in 124.6M (3x) and 1 in 143.2M (5x). Under the natural model, 5x would be 1.77× more frequent than 3x, so this shows optimizer reweighting of the bonus tail.
- Retrigger: none. Multiplier behaviour and cap are identical to base.

### 8.2 Min 2 Wild (`min2wild_200x` cost 200x, `min2wild_250x` cost 250x)

- Code: `draw_min2wild_board(p_extra)` (`game_executables.py:40-54`), with p_extra = 0.3976 / 0.4412 (`game_config.py:47-48`, mapped in `gamestate.py:11-14`).
  1. Draw an independent board (as in §5.2).
  2. Pick 2 distinct reels uniformly (`random.sample(range(5), 2)`). Each draws a Wild multiplier.
  3. Each of the other 3 reels becomes Wild independently with probability p_extra, drawing its own multiplier.
  4. Evaluate lines × M (sum of all Wild multipliers) plus scatter pay (on remaining non-Wild reels).
- **No base 4.5% Wild roll, no bonus, no mystery.** Single criteria `basegame`, quota 1.0. **Not optimized** (`run.py:37`), so it is published with weight 1 per book.

Wild-reel count: P(K = k) = C(3, k−2) · p^(k−2) · (1−p)^(5−k), and each specific set S with |S| = k has probability C(k,2)/10 · p^(k−2)(1−p)^(5−k).

| K   | 200x (p=0.3976) | 250x (p=0.4412) | E[M \| K] = K·μ_W |
| --- | --------------- | --------------- | ----------------- |
| 2   | 21.860%         | 17.449%         | 8.343             |
| 3   | 43.285%         | 41.330%         | 12.515            |
| 4   | 28.569%         | 32.632%         | 16.686            |
| 5   | 6.285%          | 8.588%          | 20.858            |

EV (DERIVED, exact, uncapped, before flooring) = Σ_S P(S)[14·ℓ(S)·|S|·μ_W + σ(S)]:

| Component                                        | 200x                  | 250x                  |
| ------------------------------------------------ | --------------------- | --------------------- |
| K=2 lines                                        | 1.6144                | 1.2886                |
| K=3 lines                                        | 18.2318               | 17.4085               |
| K=4 lines                                        | 63.2810               | 72.2808               |
| K=5 lines (84 × M)                               | 110.1260              | 150.4725              |
| Scatter (all K)                                  | 0.0038                | 0.0033                |
| **EV (x base bet)**                              | **193.257**           | **241.454**           |
| **Uncapped RTP**                                 | **96.628%**           | **96.581%**           |
| Cap loss, K=4,5 (exact)                          | −0.2453x (−0.123%)    | −0.3348x (−0.134%)    |
| Cap loss, K=2,3 (upper bound, line win ≤ 84 + 5) | ≤ 1.452x (≤ 0.726%)   | ≤ 1.330x (≤ 0.532%)   |
| 0.1x flooring loss                               | ∈ [0, 0.1x) → ≤ 0.05% | ≤ 0.04%               |
| **Capped and floored RTP range**                 | **[95.73%, 96.51%]**  | **[95.88%, 96.45%]**  |
| ARTIFACT published (unweighted 1M)               | 192.646x → **96.32%** | 240.832x → **96.33%** |
| Sampling SD of a 1M-book RTP                     | ±0.30%                | ±0.28%                |

The comment says "solved from exact EV for 96.35%". Exact uncapped EV gives 96.63% and 96.58%, so the comment's basis cannot be reproduced. It is possible only if the "exact EV" already included the cap (**UNVERIFIED**). The deployed RTP equals the published sample mean, because books are unweighted.

P(round hits 25,000x): exact contribution from K=4,5 is 1.359×10⁻⁵ (200x) and 1.850×10⁻⁵ (250x); the K=2,3 upper bound is ≤ 6.7×10⁻⁵ and ≤ 6.2×10⁻⁵. ARTIFACT `hr_max`: 1 in 76,923 (1.3×10⁻⁵) and 1 in 66,667 (1.5×10⁻⁵). These are consistent.

### 8.3 Golden Case

See §7.1.

### 8.4 Buy-mode comparison

| Mode            | Cost | Changes vs base | Guaranteed     | Bonus possible             | Optimized | Theoretical RTP                   | Published RTP (ARTIFACT) |
| --------------- | ---- | --------------- | -------------- | -------------------------- | --------- | --------------------------------- | ------------------------ |
| base            | 1    | —               | —              | yes (weights)              | yes       | 96.30% (by construction)          | 96.3%                    |
| extra_chance_3x | 3    | weights only    | —              | yes, about 4.4× more often | yes       | 96.30% (by construction)          | 96.3%                    |
| extra_chance_5x | 5    | weights only    | —              | yes, about 7.8× more often | yes       | 96.30% (by construction)          | 96.3%                    |
| min2wild_200x   | 200  | board generator | ≥ 2 Wild reels | no                         | no        | 96.628% uncapped; [95.73, 96.51]% | 96.32%                   |
| min2wild_250x   | 250  | board generator | ≥ 2 Wild reels | no                         | no        | 96.581% uncapped; [95.88, 96.45]% | 96.33%                   |
| golden_case     | 1000 | no board        | ≥ 1 letter     | no                         | no        | 96.30004%                         | 96.49%                   |

---

## 9. Configuration tables (CONFIGURED)

### 9.1 Paytable (`game_config.py:78-89`, multiples of total bet per line)

| Symbol                 | 3    | 4    | 5        |
| ---------------------- | ---- | ---- | -------- |
| W                      | —    | —    | 6.00     |
| H1                     | 0.50 | 2.00 | 6.00     |
| H2                     | 0.35 | 1.20 | 4.00     |
| H3                     | 0.25 | 0.80 | 2.50     |
| H4                     | 0.15 | 0.50 | 1.50     |
| L1                     | 0.10 | 0.30 | 1.00     |
| L2                     | 0.08 | 0.25 | 0.80     |
| L3                     | 0.05 | 0.15 | 0.50     |
| L4                     | 0.04 | 0.12 | 0.40     |
| SC (scatter, anywhere) | 0.5  | 2.0  | 5.0 (5+) |

### 9.2 Special symbols

`{"wild": ["W"], "scatter": ["SC"]}` (`game_config.py:111`). W never appears on the strip. SC is on the strip and pays only as a scatter.

### 9.3 Paylines (`game_config.py:92-107`, row 0 = top)

| #   | Rows      | #   | Rows      |
| --- | --------- | --- | --------- |
| 1   | 0 0 0 0 0 | 8   | 2 3 2 3 2 |
| 2   | 1 1 1 1 1 | 9   | 0 1 1 1 0 |
| 3   | 2 2 2 2 2 | 10  | 3 2 2 2 3 |
| 4   | 3 3 3 3 3 | 11  | 1 2 1 2 1 |
| 5   | 0 1 2 1 0 | 12  | 2 1 2 1 2 |
| 6   | 3 2 1 2 3 | 13  | 0 1 2 3 2 |
| 7   | 1 0 1 0 1 | 14  | 3 2 1 0 1 |

Because all 4 rows of a reel are identically distributed and independent, **every payline has the same win distribution**. The line shape does not affect EV, only the correlation between lines.

### 9.4 Weight tables (normalized: P = w / Σw)

`WILD_MULTIPLIER_WEIGHTS` (`game_config.py:11-15`), Σ = 8,874.32, mean 4.171587:

| Mult | 1       | 2       | 3       | 5       | 10     | 15     | 20     | 25     | 50     | 75     | 100    | 150    | 200    | 250    | 500     | 1000     |
| ---- | ------- | ------- | ------- | ------- | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------- | -------- |
| w    | 3000    | 2200    | 1600    | 1000    | 500    | 260    | 150    | 90     | 40     | 18     | 9      | 4      | 2      | 1      | 0.3     | 0.02     |
| P %  | 33.8054 | 24.7906 | 18.0296 | 11.2685 | 5.6342 | 2.9298 | 1.6903 | 1.0142 | 0.4507 | 0.2028 | 0.1014 | 0.0451 | 0.0225 | 0.0113 | 0.00338 | 0.000225 |

Worked example: P(1000x) = 0.02 / 8,874.32 = 2.2537×10⁻⁶ (1 in 443,716).

`BLUE_INCREMENT_WEIGHTS` (`game_config.py:17-21`), Σ = 6,803.32, mean 5.845675:

| +Inc | 2       | 3       | 5       | 10     | 15     | 20     | 25     | 50     | 75     | 100    | 150    | 200    | 250    | 500     | 1000     |
| ---- | ------- | ------- | ------- | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------ | ------- | -------- |
| w    | 2600    | 1800    | 1100    | 600    | 320    | 190    | 110    | 45     | 20     | 10     | 5      | 2      | 1      | 0.3     | 0.02     |
| P %  | 38.2166 | 26.4577 | 16.1686 | 8.8192 | 4.7036 | 2.7928 | 1.6169 | 0.6614 | 0.2940 | 0.1470 | 0.0735 | 0.0294 | 0.0147 | 0.00441 | 0.000294 |

`YELLOW_EXTRA_TURNS_WEIGHTS` (`:23`): +1/+2/+3 with weights 60/30/10 (P = 60%/30%/10%, mean 1.5).

Wheel (`:25-29`): trigger 0.35; RED/BLUE/YELLOW = 35/40/25; RED double-Wild 0.10.

Other scalars: `PER_REEL_WILD_PROB = 0.045` (`:43`), `GOLDEN_CASE_LETTER_PROB = 0.291759` (`:45`), `MIN2WILD_EXTRA_PROB_200X = 0.3976`, `_250X = 0.4412` (`:47-48`), `wincap = 25000.0` (`:68`), `rtp = 0.9630` (`:70`).

Optimizer-only scalars: `BASE_ONLY_RTP = 0.3924` (`:33`), `BASE_HIT_RATE = 3.44` (`:34`), `MYSTERY_TRIGGER_PROB = 0.001041`, `_EXTRA_3X = 0.004555`, `_EXTRA_5X = 0.008069` (`:35-37`), `MYSTERY_OUTCOME_WEIGHTS` (`:38-41`).

### 9.5 Bet modes and distributions (`game_config.py:145-218`)

| Mode                                   | Cost      | Distributions (criteria: quota, conditions)                                                   |
| -------------------------------------- | --------- | --------------------------------------------------------------------------------------------- |
| base, extra_chance_3x, extra_chance_5x | 1 / 3 / 5 | `freegame` 0.1 (force_freegame); `"0"` 0.4 (win_criteria 0.0); `basegame` 0.5 (no constraint) |
| golden_case                            | 1000      | `golden_case` 1.0                                                                             |
| min2wild_200x, min2wild_250x           | 200 / 250 | `basegame` 1.0                                                                                |

All conditions use the `BR0` reel weight 1 (`:132-135`), and `force_wincap=False` everywhere. The quotas set only how many books of each kind are **generated** (100k bonus / 400k zero / 500k unconstrained per 1M). They are **not** play frequencies. Play frequencies come from the optimizer.

---

## 10. Probability derivations and worked examples

### 10.1 Reel-stop probability

`random.randrange(191)` → each stop 1/191 = 0.52356%. A symbol with n stops has probability n/191. Example: L4 = 50/191 = 26.178%.

### 10.2 Line pattern probability (no Wild reels)

The 5 cells of one line are independent. For an n-of-a-kind of X with n < 5:

P = p_X^n · (1 − p_X)

For 5-of-a-kind, P = p_X^5. With no Wild reels the "W substitution" path never applies.

- Example, 3×L4: (50/191)³ × (141/191) = 0.017940 × 0.738220 = **0.013243** per line. Contribution to line RTP given no Wild reels: 14 × 0.013243 × 0.04 = 0.007416.
- Example, 5×H1: (3/191)⁵ = 9.56×10⁻¹⁰ per line.

Per-line hit probabilities with no Wild reels (DERIVED; ×14 lines gives the expected count per spin):

| Symbol | 3-kind       | 4-kind      | 5-kind      |
| ------ | ------------ | ----------- | ----------- |
| H1     | 3.814e-6     | 5.991e-8    | 9.560e-10   |
| H2     | 3.0026e-5    | 9.432e-7    | 3.059e-8    |
| H3     | 1.36002e-4   | 7.1205e-6   | 3.934e-7    |
| H4     | 5.38598e-4   | 4.51181e-5  | 4.1251e-6   |
| L1     | 1.734669e-3  | 2.17969e-4  | 3.13249e-5  |
| L2     | 3.914836e-3  | 6.55889e-4  | 1.320028e-4 |
| L3     | 7.768003e-3  | 1.667477e-3 | 4.55777e-4  |
| L4     | 1.3243283e-2 | 3.466828e-3 | 1.229372e-3 |

Line EV given no Wild reels: ℓ(∅) = 0.0033209 per line, or 0.046492 per spin.

### 10.3 Per-line EV ℓ(S) by Wild-reel set (DERIVED, exact enumeration of 9⁵ combinations)

| Wild reels S                    | ℓ(S) per line | Wild reels S      | ℓ(S) per line |
| ------------------------------- | ------------- | ----------------- | ------------- |
| ∅                               | 0.0033209     | {0,1},{0,2},{1,2} | 0.128262      |
| {0},{1},{2}                     | 0.017744      | {0,3},{1,3},{2,3} | 0.047663      |
| {3}                             | 0.008592      | {0,4},{1,4},{2,4} | 0.028408      |
| {4}                             | 0.005449      | {3,4}             | 0.019255      |
| {0,1,2},{0,1,3},{0,2,3},{1,2,3} | 0.373307      | any 4 reels       | 0.948168      |
| {0,1,4},{0,2,4},{1,2,4}         | 0.192101      | {0,1,2,3,4}       | 6.000000      |
| {0,3,4},{1,3,4},{2,3,4}         | 0.111502      |                   |               |

Check for 4 Wild reels: each line becomes 5-of-a-kind of the free reel's symbol, so ℓ = Σ_s p_s · pay₅(s) = (3·6 + 6·4 + 10·2.5 + 16·1.5 + 24·1 + 32·0.8 + 41·0.5 + 50·0.4)/191 = 181.1/191 = 0.948168. SC on the free reel pays 0.

### 10.4 Worked base-game example

S = {0} (only reel 1 Wild). P(S) = 0.045 × 0.955⁴ = 0.037431. Expected line win = 14 × 0.017744 × μ_W(4.171587) = 1.03632x. Scatter EV with 16 free cells = 0.02897x. Contribution = 0.037431 × (1.03632 + 0.02897) = 0.03987.

### 10.5 Spin-multiplier example

Two Wild reels at 5x and 10x give M = 15. A raw line total of 2.00x pays round(2.00 × 15, 2) = 30.00x, plus any scatter pay unmultiplied.

### 10.6 Bonus Markov chain (method)

State: (S = sticky Wild set, t = turns left). For each state, track probability mass P and A = E[ΣWild multipliers · 1{state}].

Transitions per spin, before the board:

- no wheel (0.65): stay;
- RED (0.1225): split by 1 or 2 Wilds and by uniform reel choice; A += (mass) × count × μ_W;
- BLUE (0.14): A += mass × μ_B if S ≠ ∅;
- YELLOW (0.0875): t += 1/2/3 with probability 0.6/0.3/0.1.

Spin EV = Σ_states 14·ℓ(S)·(A if S ≠ ∅ else P). Then t −= 1, and states with t = 0 exit. This is exact for the expectation because multiplier increments are independent of the board and of S choices, and the win is linear in M. The chain was run to the 200-spin limit.

It **ignores the 25,000x cap** (which truncates both payouts and spin count) and **ignores flooring**. Both effects lower the mean.

### 10.7 Golden Case

See §7.1. Worked example: q³ = 0.024835; 1 − (1 − q)³ = 1 − 0.708241³ = 0.644737; P(win) = 0.024835 / 0.644737 = 0.038520.

---

## 11. RTP calculation and feature contributions

### 11.1 How deployed RTP is set (optimizer)

`game_optimization.py:39-57` builds three "fences" per bonus-capable mode, serialized into `library/configs/math_config.json`. Fence order matters: `freegame` → `"0"` → `basegame`.

| Fence      | Book selector                                                            | Target                                                                             |
| ---------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `freegame` | force-record `kind = mystery` (all bonus books, including zero-pay ones) | rtp = 0.963 − 0.3924/cost; hr = 1/(P_mystery × 0.66)                               |
| `"0"`      | payout exactly 0 (remaining books)                                       | rtp 0; takes remaining probability: hr = 1/(1 − Σ 1/hr_others) (`main.rs:110-114`) |
| `basegame` | everything else (non-zero, non-bonus)                                    | rtp = 0.3924/cost; hr = 3.44                                                       |

In the Rust optimizer (`main.rs:815-826`), avg_win = hr × rtp, and fence probability = 1/hr. The pig generator uses `avg_win × bet_amount` (`main.rs:155`), so fence rtp is relative to cost and avg_win is in base-bet units.

The optimizer reweights books **inside** each fence to meet the average while fixing the fence's total probability. Within-fence RTP is therefore imposed, not natural. Consequences:

- Mode RTP is 0.963 **by construction** (asserted by `verify_optimization_input`, `optimization_config.py:172-178`).
- Base-game share: 39.24% (base), 13.08% (3x), 7.848% (5x) of cost.
- Bonus share: 57.06%, 83.22%, 88.452% of cost.

### 11.2 Feature-level breakdown, base mode

| Component                                    | Source                       | Value               |
| -------------------------------------------- | ---------------------------- | ------------------- |
| Line wins (pre-floor)                        | DERIVED exact                | 35.391%             |
| — of which spins without Wild reels          | DERIVED                      | 3.693%              |
| — of which spins with ≥ 1 Wild reel          | DERIVED                      | 31.698%             |
| Scatter pays (pre-floor)                     | DERIVED exact                | 5.189%              |
| Base total pre-floor                         | DERIVED exact                | 40.581%             |
| Flooring loss                                | COMMENT (measured)           | −1.34% (UNVERIFIED) |
| Base fence target                            | CONFIGURED                   | 39.24%              |
| Bonus fence target                           | CONFIGURED                   | 57.06%              |
| Bonus natural uncapped (at target frequency) | DERIVED upper bound          | 61.79%              |
| **Mode RTP**                                 | CONFIGURED target / ARTIFACT | **96.30% / 0.963**  |

### 11.3 Accounting in code

- Wins are accumulated in `WinManager` (`src/wins/win_manager.py`). `spin_win` is assigned to basegame or freegame by `update_gametype_wins`.
- `update_final_win` (`state.py:190-212`) caps final, base and free wins separately at the wincap and asserts consistency.
- The thread RTP print divides by `num_sims × mode_cost` (`state.py:269-277`).
- Stats use `calculate_rtp = Σ payout·w / Σ w / cost` (`distribution_functions.py:197-201`).
- Buy cost enters **only** as the denominator. Payouts are never scaled by cost.

---

## 12. Maximum win and payout caps

### 12.1 Caps

| Cap                     | Where                                                                                                                             | Effect                                                                   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Round cap 25,000x       | `GameConfig.wincap` (`game_config.py:68`); each `BetMode.max_win` (`:157-211`); set per mode in `create_books` (`run_sims.py:48`) | `update_final_win` takes `min(running_bet_win, wincap)` (`state.py:192`) |
| Bonus early stop        | `run_bonus` loop condition (`gamestate.py:59`) + `evaluate_wincap` (`executables.py:35-41`)                                       | Stops further bonus spins once the running win reaches 25,000            |
| 200 bonus spins         | `gamestate.py:58`                                                                                                                 | Safety only; probability ≈ 10⁻⁵⁶                                         |
| 0.1x payout granularity | `GameStateOverride.evaluate_finalwin` (`game_override.py:18-28`)                                                                  | Floors the round total to a 0.1x multiple **before** the cap             |

### 12.2 Flooring detail

excess = (round(total × 100) mod 10)/100. It is subtracted from freegame wins first, then basegame wins. It only affects the base/free split and the total. Example: base win 0.04 (3×L4) floors to 0, and a bonus total of 1,234.57 floors to 1,234.50.

### 12.3 Uncapped maxima (DERIVED)

| Mode                           | Uncapped maximum                                                 | Capped  |
| ------------------------------ | ---------------------------------------------------------------- | ------- |
| base / extra chance, base spin | 5 Wild reels × 1000 → M = 5000; lines 14 × 6 = 84 → **420,000x** | 25,000x |
| bonus                          | Unbounded in practice (BLUE can add +1000 per spin)              | 25,000x |
| min2wild                       | 420,000x                                                         | 25,000x |
| golden_case                    | 25,000x exactly                                                  | 25,000x |

Minimum M to cap a full-Wild board: 25,000/84 → M ≥ 298.

### 12.4 Max-win frequencies (ARTIFACT `hr_max`)

| Mode            | Max-win frequency              |
| --------------- | ------------------------------ |
| base            | 1 in 892.6M                    |
| extra_chance_3x | 1 in 124.6M                    |
| extra_chance_5x | 1 in 143.2M                    |
| min2wild_200x   | 1 in 76,923                    |
| min2wild_250x   | 1 in 66,667                    |
| golden_case     | 1 in 25.9 (theory: 1 in 25.96) |

`rules.md` says the max win should "typically" be more frequent than 1 in 10,000,000. Base and Extra Chance fall far short of that (see §14).

### 12.5 Tail checks forced by Golden Case math

P(≥10,000x) = P(≥25,000x) = 0.03852 > 0.005/0.01 (2-Star/3-Star) and > 0.002/0.005 respectively. ETL(>10,000x) = 0.963 > 0.6/0.8. These failures are **structural**: they follow from the mode definition regardless of simulation.

---

## 13. Simulation methodology and validation

### 13.1 Generator vs production

- The generator uses Python `random` (MT19937), seeded `sim + 1` per book. Weighted draws use continuous `uniform(0, Σw)`, so P = w/Σw exactly up to floating point. Bernoulli draws use `random() < p`.
- Production serves books. As long as the books on disk were made by this code (true, per the timestamps above), the published outcomes reflect this logic. Frequencies, however, reflect the **optimizer weights**, not the generator's natural frequencies (base, 3x, 5x) or the 1M-book sample (golden, min2wild).

### 13.2 Validation performed in this audit (no simulations)

| Check                                                                                        | Result                                                                                 |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Re-implemented line evaluator vs `Lines.get_lines`, 30,000 random boards (Wild reels at 30%) | 0 mismatches                                                                           |
| Exact base RTP pre-floor vs comment 0.4058                                                   | 0.405806 ✓                                                                             |
| `MYSTERY_TRIGGER_PROB*` vs formula (0.963·cost − 0.3924)/548.1                               | 0.0010411 / 0.0045550 / 0.0080690 ✓ (with 548.1 as given)                              |
| Optimizer fence avg_win                                                                      | 830.50 / 830.44 / 830.43 (ARTIFACT `statistics_summary.json` `mode_fence_info` agrees) |
| Zero-fence probability vs ARTIFACT prob_nil                                                  | 0.7086 / 0.7063 / 0.7040 vs 0.709 / 0.706 / 0.704 ✓                                    |
| Golden Case closed form vs `GOLDEN_CASE_LETTER_PROB` comment (96.30%)                        | 96.30004% ✓                                                                            |
| Min 2 Wild K-mix vs `VICE_CARTEL_TECHNICAL_SPEC.md` (22/43/29/6, 17/41/33/9)                 | 21.9/43.3/28.6/6.3, 17.4/41.3/32.6/8.6 ✓                                               |
| Min 2 Wild uncapped RTP vs comment 96.35%                                                    | 96.628% / 96.581% ✗ (see §14)                                                          |
| Bonus E[spins] closed form vs chain                                                          | 11.5108 / 13.8129 ✓                                                                    |
| Bonus natural uncapped mean vs target                                                        | 899.33 (+ base spin 899.73) vs 830.5 → gap (UNVERIFIED after cap)                      |
| Book identity base/3x/5x                                                                     | Identical sha256 ✓                                                                     |

---

## 14. Discrepancies, risks and unresolved questions

### 14.1 Code vs documentation

| #   | Document                                        | Claim                                                                                                                                                      | Code reality                                                                                                                                                         |
| --- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | `check.md`                                      | Target RTP 96.00%; "Survival Mode" with 5 lives; Hidden tiers "12 Spins or 5 Lives"; scatter pays "5x to 500x"; base 40.33%; tier EVs 173/613/4,477/11,780 | None of this exists in code. RTP 0.963, spins-only tiers, scatter 0.5/2/5, base 40.58% pre-floor, uncapped tier EVs 257/843/4,167/11,364. **Obsolete.**              |
| D2  | `test.md`                                       | Original strip 200 stops including 9 W; recommends a contiguous 4-row window                                                                               | Strip has 191 stops with no W. Rows are drawn **independently**, not as a window. A production engine using a contiguous window would have a different distribution. |
| D3  | `report.md` ("Version 3")                       | base std 14.10, HIT 97.18%, zero rate 2.82%                                                                                                                | Current ARTIFACT: std 37.87, prob_nil 0.709. **Does not describe current artifacts.**                                                                                |
| D4  | `Math Distribution & Summary.txt` ("Version 2") | base RTP 63.67%, min2wild 41.34%                                                                                                                           | Pre-optimization or pre-fix results. **Obsolete.**                                                                                                                   |
| D5  | `VICE_CARTEL_TECHNICAL_SPEC.md` §4              | "Average bonus win (published): 830.5x"                                                                                                                    | 830.5x is an **optimizer target**. The natural uncapped mean is 899.3x; the natural capped mean is UNVERIFIED.                                                       |
| D6  | `VICE_CARTEL_TECHNICAL_SPEC.md` §2 / Overview   | "Mystery check 1-in-961" presented as a runtime event                                                                                                      | No runtime check exists, and `no_bonus` is never produced. Only the bonus frequency (1 in 1,455.48) exists, through weights.                                         |
| D7  | `game_config.py:47-48` comment                  | Min 2 Wild probabilities "solved from exact EV for 96.35%"                                                                                                 | Exact uncapped EV gives 96.628% / 96.581%. Basis not reproducible (UNVERIFIED).                                                                                      |
| D8  | `VICE_CARTEL_TECHNICAL_SPEC.md` §11             | `updateFreeSpin` carries spin number/total                                                                                                                 | `gs.fs` and `gs.tot_fs` are never updated in Vice Cartel, so the event always sends `amount: 0, total: 0`.                                                           |

### 14.2 Implementation observations (no payout effect unless stated)

| #   | Observation                                                                                                                                                                                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Bonus frequency and bonus payout distribution are determined by optimizer weights, not by the configured mystery/tier probabilities. Tier mix in production is not constrained.                                                                      |
| R2  | Golden Case and Min 2 Wild RTPs are 1M-book sample values: 96.49%, 96.32%, 96.33%, with sampling SD ±0.48%, ±0.30%, ±0.28%. They are inside the 96.0–96.7% band but not equal to the theoretical values.                                             |
| R3  | Base/Extra Chance max win frequency (1 in 892.6M / 124.6M / 143.2M) is far rarer than the `rules.md` guideline of about 1 in 10M.                                                                                                                    |
| R4  | Golden Case structurally fails the Tail Probability and ETL classes (§12.5).                                                                                                                                                                         |
| R5  | `winInfo` positions are shifted to `row + 1` (`win_info_event` default `include_padding_index=True`, `src/events/events.py:140-157`), but `include_padding=False`, so the reveal board has 4 rows indexed 0–3. This is a frontend indexing mismatch. |
| R6  | `paddingPositions` is always `[0,0,0,0,0]` (`game_executables.py:19`), because there are no real stop positions.                                                                                                                                     |
| R7  | BLUE with no sticky Wild emits `stickyWildUpdate` but no `wheelSpin`. YELLOW and RED emit both.                                                                                                                                                      |
| R8  | `evaluate_wincap` runs only after positive **line** wins, not after scatter pays. This has no payout effect because the final cap uses `min`.                                                                                                        |
| R9  | The `simulation_seed` argument is ignored (`reset_seed(sim)`), so modes with identical code paths and distributions share books. This is intentional per the run comments but couples modes.                                                         |
| R10 | There are no Vice-Cartel-specific automated tests.                                                                                                                                                                                                   |

### 14.3 Unverified items and what is needed

| Item                                                   | Status                                                                  | What would settle it                                                                                                                                                                                           |
| ------------------------------------------------------ | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Base flooring loss 0.0134 and `BASE_ONLY_RTP = 0.3924` | UNVERIFIED (measured)                                                   | The exact distribution of per-spin total win (correlated lines) or a large simulation; or the unweighted mean of `basegame` + `"0"` books in `library/lookup_tables/lookUpTable_base.csv` joined with criteria |
| `BASE_HIT_RATE = 3.44`                                 | UNVERIFIED (measured; ARTIFACT 3.432 is consistent)                     | As above                                                                                                                                                                                                       |
| "548.1x EV per mystery check" (830.45x per bonus)      | UNVERIFIED                                                              | The unweighted mean payout of `freegame` books in the base books file (natural, capped, floored); or a capped analytic or simulated bonus model                                                                |
| Natural capped bonus EV per tier, and P(cap) per tier  | UNVERIFIED                                                              | A distributional model of the bonus (not just expectation) or simulation                                                                                                                                       |
| Deployed effective tier mix and bonus frequency        | UNVERIFIED (targets known)                                              | Weight-sum per `outcome` force key over `lookUpTable_<mode>_0.csv`                                                                                                                                             |
| Min 2 Wild K=2,3 cap loss (only bounded)               | Partly bounded                                                          | Exact X-distribution for 2–3 free reels (9⁸ enumeration per subset)                                                                                                                                            |
| RGS book-selection algorithm and bet-level templates   | Outside repository                                                      | RGS documentation or source                                                                                                                                                                                    |
| Variance / volatility                                  | ARTIFACT only (std 37.87 / 22.83 / 17.77 / 3.02 / 2.77 / 4.82 per cost) | Theoretical value only for Golden Case (4.811); others need full distributions                                                                                                                                 |

---

## 15. Source-code reference index

| Mechanic                     | Location                                                                                                 |
| ---------------------------- | -------------------------------------------------------------------------------------------------------- |
| Probability tables           | `games/vice_cartel/game_config.py:11-29,43-48`                                                           |
| Optimizer-only scalars       | `game_config.py:31-41`                                                                                   |
| Wincap / RTP                 | `game_config.py:68,70`                                                                                   |
| Grid, paytable, paylines     | `game_config.py:74-107`                                                                                  |
| Special symbols, scatter pay | `game_config.py:111,113`                                                                                 |
| Reels                        | `game_config.py:125-129`; `reels/BR0.csv`; `src/config/config.py:122-140`                                |
| Distributions & bet modes    | `game_config.py:132-218`                                                                                 |
| Independent board draw       | `game_executables.py:15-25`                                                                              |
| Base Wild reels              | `game_executables.py:27-38`; `game_calculations.py:17-22`                                                |
| Min 2 Wild board             | `game_executables.py:40-54`; `gamestate.py:11-14,31-38`                                                  |
| Line evaluation × M          | `game_executables.py:56-73`; `src/calculations/lines.py:28-126`; `src/wins/multiplier_strategy.py:32-41` |
| Scatter                      | `game_executables.py:75-80`; `game_calculations.py:33-45`                                                |
| Wheel                        | `game_executables.py:82-104`; `game_calculations.py:48-65`                                               |
| Bonus spin                   | `game_executables.py:106-127`                                                                            |
| Bonus loop                   | `gamestate.py:54-69`                                                                                     |
| Tier draw                    | `gamestate.py:8,74-78`                                                                                   |
| Tier setup                   | `game_override.py:42-57`                                                                                 |
| Golden Case                  | `game_executables.py:129-136`; `game_calculations.py:68-74`; `gamestate.py:25-29`                        |
| Flooring                     | `game_override.py:18-28`                                                                                 |
| Repeat rules                 | `game_override.py:30-40`                                                                                 |
| Final win / cap              | `src/state/state.py:190-212`; `src/executables/executables.py:35-41,97-100`                              |
| Weighted draw                | `src/calculations/statistics.py:5-17`                                                                    |
| Seeding                      | `src/state/state.py:88-94`; `gamestate.py:20`                                                            |
| Criteria allocation          | `src/state/run_sims.py:83-105`                                                                           |
| Book payout encoding         | `src/state/books.py:27-36`                                                                               |
| Optimizer targets            | `game_optimization.py:12,39-57,60-74`; `optimization_program/src/main.rs:94-114,781-887`                 |
| Lookup checks                | `utils/rgs_verification.py:100-131`                                                                      |
| RTP formula                  | `utils/analysis/distribution_functions.py:197-201`                                                       |
| Pipeline                     | `games/vice_cartel/run.py`                                                                               |

---

## 16. Final audit inventory

| Mode / feature                                     | Audited    | Exact math derived            | Notes                                         |
| -------------------------------------------------- | ---------- | ----------------------------- | --------------------------------------------- |
| Base grid, strips, symbol probabilities            | ✓          | ✓                             | §5.2                                          |
| Full-reel Wilds, multiplier table, spin multiplier | ✓          | ✓                             | §5.3–5.4                                      |
| Line evaluation (incl. W/SC edge cases)            | ✓          | ✓ (cross-checked vs SDK)      | §5.5, §10.3                                   |
| Scatter pay                                        | ✓          | ✓                             | §5.7                                          |
| Base RTP pre-floor                                 | ✓          | ✓ 40.5806%                    | flooring loss UNVERIFIED                      |
| Mystery trigger (optimizer-only)                   | ✓          | ✓ targets                     | no runtime roll                               |
| 4 bonus tiers, wheel RED/BLUE/YELLOW, sticky Wilds | ✓          | ✓ expected spins, uncapped EV | capped EV UNVERIFIED                          |
| Extra Chance 3x / 5x                               | ✓          | ✓ targets                     | identical books to base                       |
| Min 2 Wild 200x / 250x                             | ✓          | ✓ uncapped EV, partial cap    | §8.2                                          |
| Golden Case (max-win-or-nothing)                   | ✓          | ✓ closed form                 | deployed 96.49% sample                        |
| MWON                                               | ✓ searched | n/a                           | not a Vice Cartel mode (Clockwork Heist only) |
| 25,000x cap, 0.1x flooring, 200-spin limit         | ✓          | ✓ maxima                      | §12                                           |
| Optimizer fences and accounting                    | ✓          | ✓                             | §11                                           |
| RGS selection / bet levels                         | ✗          | —                             | not in repository                             |
