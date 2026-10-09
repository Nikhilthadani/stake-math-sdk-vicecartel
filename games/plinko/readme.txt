Plinko Base Game — Stake Engine Port
=====================================

Ported from engine-plinko to the Stake Math SDK.

Game mechanics
--------------
- Ball drops through a triangular peg board.
- At each row the ball bounces left (0) or right (1) with equal 50/50 probability.
- The final landing slot determines the payout multiplier.
- Supported rows: 8–16.  Risk levels: low, medium, high.

What is included
----------------
- All 27 base-game configurations (9 rows × 3 risks).
- Each configuration is a separate BetMode with its own books/lookup table.
- Multiplier tables are an exact copy from the original engine-plinko.
- No buy features, bonus rounds, or free spins.

RTP
---
Analytical RTP = Σ C(n,k)/2^n × multiplier[k] for k in 0…n.
Values range from ~96% to ~99% depending on configuration.
Run the script to see the full table.

Running
-------
From the SDK root:
    python games/plinko/run.py

Default: 10M sims per mode, compression enabled.
Adjust NUM_SIMS and COMPRESSION in run.py as needed.
