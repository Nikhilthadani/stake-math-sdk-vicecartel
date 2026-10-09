"""Plinko-specific events for the Stake Engine frontend."""

from src.events.events import *


def plinko_result_event(gamestate, path, final_slot, rows, risk, multiplier):
    """Emit the ball drop path and payout result.

    This single event gives the frontend everything it needs to animate
    the ball and display the win:
      - path:      list of 0/1 (left/right at each peg)
      - slotPath:  cumulative rightward count after each row
      - finalSlot: landing bucket index (0 … rows)
      - multiplier: payout multiplier for that bucket
    """
    slot_path = []
    pos = 0
    for bit in path:
        pos += bit
        slot_path.append(pos)

    event = {
        "index": len(gamestate.book.events),
        "type": "plinkoResult",
        "rows": rows,
        "riskLevel": risk,
        "path": path,
        "slotPath": slot_path,
        "finalSlot": final_slot,
        "multiplier": multiplier,
        "totalWin": int(round(multiplier * 100, 0)),
    }
    gamestate.book.add_event(event)
