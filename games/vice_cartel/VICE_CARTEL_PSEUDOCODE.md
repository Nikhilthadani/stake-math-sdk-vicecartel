# Vice Cartel — Implementation in Pseudocode

> **Outdated (math v1).** The live math is v2.0: see `vc_math/docs/MATH_SPEC.md` for the math and
> `frontend/FRONTEND_INTEGRATION.md` for modes, events and config.

The simplest possible walk-through of what the code does on every spin.
Each block names the real function it mirrors, so you can jump from here to the code.

---

## 1. One Spin (the main loop) — `gamestate.py → run_spin`

```
FUNCTION run_spin():
    REPEAT until the result fits the book we are trying to make:
        clear the round

        IF mode == "golden_case":
            run_golden_case()
            finish_round()
            STOP

        IF mode == "min2wild_200x" or "min2wild_250x":
            draw_min2wild_board()
            pay_lines()
            pay_scatters()
            finish_round()
            STOP

        # base, extra_chance_3x, extra_chance_5x
        draw_normal_board()
        pay_lines()
        pay_scatters()

        IF this book is a "freegame" (bonus) book:
            tier = mystery_trigger()
            run_bonus(tier)

        finish_round()
```

> The bonus is NOT rolled live. The simulator makes separate "bonus books",
> and the optimizer decides how often they show up (~1 in 1,455 base spins).

---

## 2. Drawing the Board — `game_executables.py`

```
FUNCTION draw_random_symbols():
    FOR each of 5 reels:
        FOR each of 4 rows:
            cell = random symbol from reel strip BR0     # each cell picked independently

FUNCTION draw_normal_board():
    draw_random_symbols()
    wild_reels = {}
    FOR each reel:
        IF random() < 4.5%:                              # PER_REEL_WILD_PROB
            wild_reels[reel] = pick_wild_multiplier()    # 1x … 1000x, weighted
            fill whole reel with W

FUNCTION draw_min2wild_board(extra_prob):           # extra_prob = 39.76% (200x) or 44.12% (250x)
    draw_random_symbols()
    pick 2 random reels → make them Wild (with multiplier)
    FOR each other reel:
        IF random() < extra_prob:
            make it Wild (with multiplier)
```

---

## 3. Paying Wins — `game_executables.py`

```
FUNCTION pay_lines():
    spin_mult = SUM of all wild multipliers on screen   # no wilds → 1
    line_win  = check 14 paylines against paytable
    win      += line_win × spin_mult

FUNCTION pay_scatters():
    n = count "SC" anywhere on the board
    IF n == 3:  win += 0.5x
    IF n == 4:  win += 2x
    IF n >= 5:  win += 5x
    # scatters only pay — they do NOT trigger the bonus
```

---

## 4. Mystery Trigger — `gamestate.py → _forced_mystery_outcome`

```
FUNCTION mystery_trigger():
    tier = weighted pick:
        normal_bonus        40
        super_bonus         20
        hidden_bonus         5
        super_hidden_bonus   1
    send event "mysteryTrigger"
    RETURN tier
```

> The full table also has `no_bonus = 34`. Those "trigger but nothing" cases
> are already counted in how often bonus books appear, so they aren't simulated here.

---

## 5. The Bonus Round — `gamestate.py → run_bonus`

```
TIERS:
    normal_bonus        → 10 spins, 0 starting wilds, 1x
    super_bonus         → 10 spins, 1 starting wild,  2x
    hidden_bonus        → 12 spins, 2 starting wilds, 3x
    super_hidden_bonus  → 12 spins, 3 starting wilds, 5x

FUNCTION run_bonus(tier):
    spins_left   = TIERS[tier].spins
    sticky_wilds = place TIERS[tier].start_wilds on random reels, each with start_mult

    WHILE spins_left > 0 AND win cap not hit AND spins played < 200:
        spin_wheel(sticky_wilds, spins_left)     # may change wilds or add spins
        bonus_spin(sticky_wilds)
        spins_left -= 1
```

### 5a. The Wheel — `resolve_wheel`

```
FUNCTION spin_wheel():
    IF random() >= 35%: RETURN                  # wheel doesn't show this spin

    colour = weighted pick: RED 35, BLUE 40, YELLOW 25

    RED:    add 1 new sticky wild (10% chance: 2) on empty reels, random multiplier
    BLUE:   pick one existing sticky wild, add +2 … +1000 to its multiplier
            (does nothing if there are no sticky wilds yet)
    YELLOW: spins_left += 1, 2 or 3   (weights 60 / 30 / 10)
```

### 5b. One Bonus Spin — `run_bonus_spin`

```
FUNCTION bonus_spin(sticky_wilds):
    draw_random_symbols()
    fill every sticky reel with W
    spin_mult = SUM of sticky wild multipliers   # none → 1
    win += line_win × spin_mult
    # no scatter pay in the bonus
```

---

## 6. Golden Case (1000x buy) — `run_golden_case`

```
FUNCTION run_golden_case():
    REPEAT:
        letters = 0
        FOR each of M, A, X:
            IF random() < 29.18%: letters += 1
    UNTIL letters >= 1                          # always shows at least 1 letter

    IF letters == 3:  win = 25,000x (max win)
    ELSE:             win = 0
```

---

## 7. Finishing the Round — `game_override.py → evaluate_finalwin`

```
FUNCTION finish_round():
    round total down to a multiple of 0.1x     # RGS pays in 0.1x steps
    (take the cut-off bit from bonus wins first, then base wins)
    cap total at 25,000x
    save the book
```

---

## 8. Which Mode Does What

| Mode              | Cost  | Board              | Bonus possible? |
|-------------------|-------|--------------------|-----------------|
| base              | 1x    | normal             | yes (~1 in 1,455) |
| extra_chance_3x   | 3x    | normal             | yes (~1 in 333)   |
| extra_chance_5x   | 5x    | normal             | yes (~1 in 188)   |
| min2wild_200x     | 200x  | 2 forced wilds     | no                |
| min2wild_250x     | 250x  | 2 forced wilds     | no                |
| golden_case       | 1000x | letter reveal only | no                |
