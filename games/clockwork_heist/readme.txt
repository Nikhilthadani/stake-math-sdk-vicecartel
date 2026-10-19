# Clockwork Heist

Stake Engine port of engine-clockwork (RTPDeck RGS). Same math: every number comes from
game_config.json, a copy of engine-clockwork/src/config/game_config.json (keep them identical).
Reference figures: Slot_Game_PAR_Sheet.xlsx.

5 reels x 4 rows, 40 left-to-right paylines, pays in multiples of total bet, max win 25,000x.

Base game:
  Wilds (WD, never on reel 1) carry a 2x/3x/5x multiplier (weights 6/3/1). Multipliers of the
  wilds in a winning run add up (2x + 3x = 5x); a run without wilds pays x1.
  3 scatters (SC, one each on reels 1, 3, 5) trigger 8 free spins; the trigger spin's line win
  is paid on top.

Free spins (free reels, no scatters, no retrigger):
  Sticky wilds: every wild that lands stays locked with its multiplier for the session.
  Gold Meter: each wild landing on an empty cell is a key; 5 keys = +3 spins, extra keys carry over
  (at most 12 locked cells, so at most 14 spins).
  Session wins below 10x are topped up to 10x (not when the session hit the cap).

Modes:
  base   1x     natural game
  bonus  100x   Bonus Buy: buy reels always show 3 scatters and never pay, then a normal session
  mwon   1000x  Max Win or Nothing: wins 25,000x with probability 0.0384 (96.00% RTP), shown as a
                5-of-a-kind line; a loss shows a 4-of-a-kind near miss and pays nothing

25,000x is unreachable in base and bonus (PAR "Assumptions & Gaps" G-01), so those modes have no
wincap criteria. mwon lookup weights are set exactly by run.py, never by the optimizer.

Files:
  game_config.py        config + load-time guards (strip counts, wild-free reel 1, buy reels)
  gamestate.py          round flow: base / bonus / mwon, free-spins session
  game_calculations.py  sticky wilds, Gold Meter, min award, mwon screen sampling
  game_executables.py   line evaluation and win events (no padding rows)
  game_override.py      wild multipliers, repeat rules, fast event copy, round total paid rounded
                        down to 0.1x (Stake payout step; engine-clockwork pays the 0.05x steps exactly)
  game_events.py        goldMeter, freeSpinMinAward, mwonResult events
  run.py                book generation, configs, lookup weights: natural base odds, base and bonus
                        tilted onto GameConfig.rtp (96.35%), exact mwon weights
  check_parity.py       natural-play parity check against the PAR sheet
  FRONTEND_EVENTS.md    book/event format for the frontend (example_books.json: real books)

Commands (from the SDK root):
  python games/clockwork_heist/check_parity.py         # 10M base, 1M bonus, 200k mwon vs PAR
  python games/clockwork_heist/run.py                  # books + lookup tables + publish_files
