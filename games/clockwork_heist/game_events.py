"""Clockwork Heist events (on top of the SDK's standard events)."""

from src.events.events import *

GOLD_METER = "goldMeter"
FREE_SPIN_MIN_AWARD = "freeSpinMinAward"
VAULT_START = "vaultStart"
VAULT_RESPIN = "vaultRespin"
VAULT_END = "vaultEnd"


def vault_start_event(gamestate, respins_left: int) -> None:
    """Max Win or Nothing start grid: the starting Vault Keys, reel by reel, top to bottom."""
    keys = [
        {"reel": reel, "row": row, "multiplier": multiplier}
        for (reel, row), multiplier in sorted(gamestate.vault.items())
    ]
    event = {
        "index": len(gamestate.book.events),
        "type": VAULT_START,
        "keys": keys,
        "respinsLeft": respins_left,
    }
    gamestate.book.add_event(event)


def vault_respin_event(gamestate, respin: int, new_keys: list, respins_left: int) -> None:
    """One respin: keys that landed on it (empty when none did), keys on the grid and respins left."""
    event = {
        "index": len(gamestate.book.events),
        "type": VAULT_RESPIN,
        "respin": respin,
        "newKeys": new_keys,
        "keys": len(gamestate.vault),
        "respinsLeft": respins_left,
    }
    gamestate.book.add_event(event)


def vault_end_event(gamestate, respins: int, full: bool, multiplier_sum: int, min_award_applied: bool,
                    amount: float) -> None:
    """End of the vault: the round's win (full grid = max win, else the multiplier sum, at least the minimum)."""
    event = {
        "index": len(gamestate.book.events),
        "type": VAULT_END,
        "respins": respins,
        "keys": len(gamestate.vault),
        "full": full,
        "multiplierSum": multiplier_sum,
        "minAwardApplied": min_award_applied,
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
