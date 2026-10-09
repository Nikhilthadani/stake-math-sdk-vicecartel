Plinko Base Game — Stake Engine Port
=====================================

Ported from engine-plinko to the Stake Math SDK.

Game mechanics
--------------
- Ball drops through a triangular peg board.
- At each row the ball bounces left (0) or right (1) with equal 50/50 probability.
- The final landing slot determines the payout multiplier.
- Supported rows: 8, 10, 12, 14, 16.  Risk levels: low, medium, high.

What is included
----------------
- All 15 base-game configurations (5 rows × 3 risks).
- Each configuration is a separate BetMode with its own books/lookup table.
- Multiplier tables tuned to 96.1% RTP with sigma >= 0.6 on all modes.
- No buy features, bonus rounds, or free spins.

Stake compliance
----------------
- RTP: 96.0-96.7% band (target 96.1%)
- Sigma: >= 0.6 on all modes (low risk tuned to ~0.65)
- Modes: 15 (max 20)
- Events: 10M per mode (max 10M)
- Files: .jsonl.zst compressed (well under 4.2 GB each)
- Payout format: uint64, hundredths of base bet

Running
-------
From the SDK root:
    python games/plinko/run.py

Default: 10M sims per mode, compression enabled.
Adjust NUM_SIMS and COMPRESSION in run.py as needed.
