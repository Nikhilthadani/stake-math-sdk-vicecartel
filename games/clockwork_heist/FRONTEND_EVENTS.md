# Clockwork Heist: Stake Engine response format

This replaces the engine-clockwork play response (`PlayResultDto`: `result.spins[]`,
`result.freeSpins`, `fair`, `roundTransaction`). On Stake Engine every round is a
pre-generated **book**; the RGS returns it inside `round` from `POST /wallet/play`:

```json
{ "balance": { "amount": 100000, "currency": "USD" }, "round": { ... book ... } }
```

The book (the part the game reads):

```json
{ "id": 123, "payoutMultiplier": 27830, "events": [ { "index": 0, "type": "reveal", ... }, ... ] }
```

Real books for every round shape are in [`example_books.json`](example_books.json).

## Global rules

| Topic | Old (RTPDeck RGS) | New (Stake Engine) |
|---|---|---|
| Win amounts | Money, 2 decimals (`amount`, `winAmount`) | Integer **bet multiple x 100**: `1150` = 11.5x bet. Display: `value / 100 * bet` |
| Bet / balance | Money, 2 decimals | RGS integer, 1,000,000 = 1.00 currency unit (`100000` = 0.10) |
| Round total | `result.winAmount`, `result.multiplier` | `payoutMultiplier` (same value as the `finalWin` event), rounded **down** to 0.1x (see below) |
| Max win reached | `result.maxWin` | a `wincap` event is present |
| Board | `spins[i].reels[reel][row]`, plain strings | `reveal.board[reel][row]`, objects (see below) |
| Wild multipliers | `spins[i].wilds[]` | on the board cell: `{ "name": "WD", "wild": true, "multiplier": 3 }` |
| Scatter | `"SC"` in `reels` | `{ "name": "SC", "scatter": true }` |
| Rows | 0-3, top to bottom | unchanged: 0-3, top to bottom, no padding rows |
| Payline index | 0-based | unchanged: 0-based (`meta.lineIndex`) |
| Symbols | `M1`-`M6`, `F1`-`F5`, `WD`, `SC` | unchanged |
| Spin type | `spins[i].type`: base / buy / free / mwon | `reveal.gameType`: `basegame` / `freegame`; the mode is the one you sent in `/wallet/play` |
| Fairness (`fair`) | seeds + config hash | removed: outcomes are pre-generated and weighted |
| Wallet (`roundTransaction`, `betAmount`) | in engine response | handled by the Stake RGS (`/wallet/play`, `/wallet/end-round`) |

Stake pays multipliers in steps of 0.1x (`payoutMultiplier` is a multiple of 10), but the
paytable has 0.05x steps (e.g. F1 3-of-a-kind 0.15x). The round is paid rounded down:
`finalWin` / `payoutMultiplier` can be 0.05x below the last `setTotalWin` (e.g. `setTotalWin`
1225, `finalWin` 1220). `winInfo`, `setWin`, `setTotalWin` and `freeSpinEnd` keep the exact
paytable values; show `finalWin` as the paid amount.

Bet modes (`mode` in `/wallet/play`): `base` (cost 1x), `bonus` (Bonus Buy, 100x),
`mwon` (Max Win or Nothing, 1000x). Debit = bet x cost.

## Board cell

```json
{ "name": "M1" }                                   // normal symbol
{ "name": "WD", "wild": true, "multiplier": 2 }    // wild, multiplier 2 / 3 / 5
{ "name": "SC", "scatter": true }                  // scatter (base and buy reels only)
```

## Events

Every event has `index` (position in `events`) and `type`. Amounts are bet multiple x 100.

### Standard events

| type | Fields | Old equivalent |
|---|---|---|
| `reveal` | `board` (5 reels x 4 rows), `gameType`, `paddingPositions` (reel stop of each reel), `anticipation` | `spins[i].reels` + `spins[i].wilds` |
| `winInfo` | `totalWin`, `wins[]` | `spins[i].wins[]` |
| `setWin` | `amount` (this spin's win), `winLevel` (1-10) | `spins[i].amount` |
| `setTotalWin` | `amount`: running round total (trigger spin + free spins so far) | (new) |
| `freeSpinTrigger` | `totalFs` (8), `positions[]` of the 3 scatters | `freeSpins !== null` |
| `updateFreeSpin` | sent before each free spin: `amount` = free spins **already played** (0 on the first), `total` = spins in the session so far, Gold Meter awards included | spin number = `amount + 1` (spins left: `goldMeter.spinsLeft`) |
| `freeSpinEnd` | `amount`: session win **including** the 10x top-up, **excluding** the trigger spin; `winLevel` | `freeSpins.amount` |
| `wincap` | `amount` (2500000) | `maxWin: true` |
| `finalWin` | `amount` = `payoutMultiplier`: round total rounded down to 0.1x | `multiplier` |

`winInfo.wins[]` entry:

```json
{
  "symbol": "F3", "kind": 3, "win": 50,
  "positions": [{ "reel": 0, "row": 1 }, { "reel": 1, "row": 1 }, { "reel": 2, "row": 0 }],
  "meta": { "lineIndex": 25, "multiplier": 5, "winWithoutMult": 10, "globalMult": 1, "lineMultiplier": 5 }
}
```

| New | Old (`LineWinDto`) |
|---|---|
| `meta.lineIndex` | `line` |
| `symbol` | `symbol` |
| `kind` | `count` |
| `meta.multiplier`: sum of wild multipliers on the run, 1 without wilds | `multiplier` |
| `win` (x100) | `amount` (money) |
| `meta.winWithoutMult`: paytable value | (new) |
| `positions` | (new; was derived from the line) |

`anticipation`: one value per reel; a reel with a value > 0 should spin with scatter
anticipation, in that order (e.g. `[0, 0, 0, 1, 2]` after scatters on reels 1 and 3).

`winLevel` (`setWin`): 1 = <0.1x, 2 = <1x, 3 = <2x, 4 = <5x, 5 = <15x, 6 = <30x,
7 = <50x, 8 = <100x, 9 = <25,000x, 10 = max win. `freeSpinEnd` uses
1 = <1x, 2 = <5x, 3 = <10x, 4 = <20x, 5 = <50x, 6 = <100x, 7 = <500x, 8 = <2,000x,
9 = <25,000x, 10 = max win.

### Clockwork Heist events

| type | Fields | Old equivalent |
|---|---|---|
| `goldMeter` | after every free-spin `reveal`: `newWilds[]` `{reel, row, multiplier}` (wilds that locked on this spin, each is a key), `lockedWilds` (sticky wilds on screen), `keys` (meter after this spin, 0-4), `spinsAdded` (0, 3 or 6), `spinsLeft` | `spins[i].keys`, `spins[i].spinsAdded`, `spins[i].spinsLeft` |
| `freeSpinMinAward` | `spinsWin` (session win before top-up), `topUp`, `amount` (1000 = 10x) | `freeSpins.minAwardApplied: true` |
| `mwonResult` | `win` (bool), `amount` (2500000 or 0) | `mode: "mwon"` + `multiplier` |

Sticky wilds have no separate event: on every free-spin `reveal` the locked wilds
are already on the board as `WD` with their original multiplier. `goldMeter.newWilds`
says which of them landed on this spin; all others were locked earlier.

Gold Meter: 5 keys add 3 spins; extra keys carry over (`keys` = `lockedWilds % 5`).
When spins are added, the next `updateFreeSpin.total` includes them.

## Event order per round

`[...]` = only when it applies. `( ... ) x N` = once per free spin.

**base, no win**
```
reveal > setTotalWin > finalWin
```

**base, line win**
```
reveal > winInfo > setWin > setTotalWin > finalWin
```

**base, free spins triggered** (the trigger spin can also pay lines)
```
reveal > [winInfo > setWin] > setTotalWin > freeSpinTrigger >
( updateFreeSpin > reveal > goldMeter > [winInfo > setWin] > setTotalWin ) x N >
[freeSpinMinAward > setTotalWin] > freeSpinEnd > finalWin
```

**bonus** (Bonus Buy): same as the free-spins round above. The first `reveal`
(`gameType: basegame`, buy reels) always shows 3 scatters and never pays.

**mwon, win**
```
reveal > mwonResult > winInfo > wincap > setTotalWin > finalWin
```
`winInfo` holds one line: the first 5-of-a-kind on screen, `win` = 2500000,
`meta.multiplier` = 1 (the prize is flat, not the paytable). There is no `setWin`
once the cap is reached; use `wincap.amount`.

**mwon, loss**
```
reveal > mwonResult > setTotalWin > finalWin
```
The screen shows a 4-of-a-kind near miss and nothing pays.

**max win in free spins**: `wincap` follows the `winInfo` that reaches 25,000x,
the session ends (no more `updateFreeSpin`) and no minimum award applies. With the
current math this does not happen in `base` or `bonus` (largest simulated session
6,582x); only `mwon` pays 25,000x.

## Old response to new events, field by field

| Old field | New source |
|---|---|
| `result.mode` | the mode sent to `/wallet/play` |
| `result.bet`, `result.betAmount` | the bet sent to `/wallet/play` (x mode cost) |
| `result.winAmount` | `payoutMultiplier / 100 * bet` |
| `result.multiplier` | `payoutMultiplier / 100` |
| `result.maxWin` | `wincap` event present |
| `result.spins[0]` | first `reveal` + its `winInfo` / `setWin` |
| `result.spins[i > 0]` | each `updateFreeSpin > reveal > goldMeter > [winInfo > setWin]` group |
| `spins[i].type` | `reveal.gameType` (+ mode) |
| `spins[i].reels` | `reveal.board[r][row].name` |
| `spins[i].wilds` | `reveal.board` cells with `wild: true` |
| `spins[i].wins` | `winInfo.wins` |
| `spins[i].amount` | `setWin.amount` (absent = 0) |
| `spins[i].keys` / `spinsAdded` / `spinsLeft` | `goldMeter.keys` / `spinsAdded` / `spinsLeft` |
| `freeSpins.spins` | number of `updateFreeSpin` events |
| `freeSpins.minAwardApplied` | `freeSpinMinAward` event present |
| `freeSpins.amount` | `freeSpinEnd.amount` |
| `fair` | (removed) |

## Static game data

Generated with the books into `library/configs/config_fe_clockwork_heist.json`
(replaces the old `GameConfigResponseDto` from `/balance`):

| Key | Content |
|---|---|
| `numReels`, `numRows` | 5, `[4, 4, 4, 4, 4]` |
| `paylines` | `{ "0": [0,0,0,0,0], ... }`, 40 lines, 0-based keys |
| `symbols` | per symbol: `paytable` (`[{"5": 20.0}, {"4": 5.0}, {"3": 1.5}]`, x bet, not x100) or `special_properties` |
| `betModes` | `base` / `bonus` / `mwon`: `cost`, `rtp`, `max_win`, `buyBonus`, `feature` |
| `paddingReels` | base and free reel strips (for reel-spin animation) |

Not in the file, fixed by the game rules: wild multipliers 2x / 3x / 5x, 8 free spins,
5 keys = +3 spins, 10x minimum session award, 25,000x max win.
