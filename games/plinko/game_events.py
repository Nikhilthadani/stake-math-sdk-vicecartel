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


def wheel_spin_event(gamestate, final_slot, base_multiplier, segment, wheel_value, multiplier):
    """Emit the wheel spin triggered by landing in a wheel slot.

      - segment:        index into config wheel segments (where the wheel stops)
      - wheelValue:     multiplier on that segment
      - baseMultiplier: slot multiplier before the wheel
      - multiplier:     final payout multiplier (base × wheel)
    """
    event = {
        "index": len(gamestate.book.events),
        "type": "wheelSpin",
        "finalSlot": final_slot,
        "segment": segment,
        "wheelValue": wheel_value,
        "baseMultiplier": base_multiplier,
        "multiplier": multiplier,
        "totalWin": int(round(multiplier * 100, 0)),
    }
    gamestate.book.add_event(event)
