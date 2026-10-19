"""Clockwork Heist events (on top of the SDK's standard events)."""

from src.events.events import *

GOLD_METER = "goldMeter"
FREE_SPIN_MIN_AWARD = "freeSpinMinAward"
MWON_RESULT = "mwonResult"


def mwon_result_event(gamestate, is_win: bool, amount: float) -> None:
    """Max Win or Nothing outcome, sent right after the reveal."""
    event = {
        "index": len(gamestate.book.events),
        "type": MWON_RESULT,
        "win": is_win,
        "amount": int(round(amount * 100, 0)),
    }
    gamestate.book.add_event(event)


def gold_meter_event(gamestate, new_wilds: list, spins_added: int) -> None:
    """After each free-spin reveal: wilds that just locked (each is a key) and the meter state."""
    event = {
        "index": len(gamestate.book.events),
        "type": GOLD_METER,
        "newWilds": new_wilds,
        "lockedWilds": len(gamestate.locked_wilds),
        "keys": len(gamestate.locked_wilds) % gamestate.config.free_spins["keys_per_award"],
        "spinsAdded": spins_added,
        "spinsLeft": gamestate.tot_fs - gamestate.fs,
    }
    gamestate.book.add_event(event)


def min_award_event(gamestate, spins_win: float, top_up: float) -> None:
    """Free-spins session paid less than the minimum and was topped up."""
    event = {
        "index": len(gamestate.book.events),
        "type": FREE_SPIN_MIN_AWARD,
        "spinsWin": int(round(spins_win * 100, 0)),
        "topUp": int(round(top_up * 100, 0)),
        "amount": int(round(gamestate.config.free_spins["min_award"] * 100, 0)),
    }
    gamestate.book.add_event(event)
