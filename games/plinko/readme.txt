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
- 5 "wheel" buy modes ({rows}_wheel), cost 1.3x, medium risk.
- Each configuration is a separate BetMode with its own books/lookup table.
- Multiplier tables tuned to 96.1% RTP with sigma >= 0.6 on all modes.
- No bonus rounds or free spins.

Wheel buy feature
-----------------
- Some slots on each wheel table are wheel slots (see WHEEL_TABLES in game_config.py):
    8: 2, 6   10: 4, 6   12: 4, 8   14: 5, 7, 9   16: 6, 10
- Landing in a wheel slot spins a 20-segment wheel:
    13 × 1x, 4 × 2x, 2 × 5x, 1 × 10x   (E = 2.05)
  Payout = slot multiplier × wheel value.
- RTP per unit cost:  sum_k C(n,k)/2^n · m_k · (E[wheel] if k is a wheel slot else 1) / 1.3
- Events: plinkoResult, then wheelSpin (segment, wheelValue, baseMultiplier, multiplier).

Stake compliance
----------------
- RTP: 96.0-96.7% band (target 96.1%)
- Sigma: >= 0.6 on all modes (low risk tuned to ~0.65)
- Modes: 20 (max 20)
- Events: 10M per mode (max 10M)
- Files: .jsonl.zst compressed (well under 4.2 GB each)
- Payout format: uint64, hundredths of base bet

Running
-------
From the SDK root:
    python games/plinko/run.py

Default: 10M sims per mode, compression enabled.
Adjust NUM_SIMS and COMPRESSION in run.py as needed.
