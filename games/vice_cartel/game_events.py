"""Vice Cartel — custom events for the frontend."""

from src.events.events import (
    reveal_event,
    win_info_event,
    set_win_event,
    set_total_event,
    final_win_event,
    wincap_event,
    update_freespin_event,
    freespin_end_event,
)


def wild_reel_event(gamestate, reel_index: int, multiplier: int) -> None:
    event = {"index": len(gamestate.book.events), "type": "wildReel", "reel": reel_index, "multiplier": multiplier}
    gamestate.book.add_event(event)

def spin_multiplier_event(gamestate, spin_multiplier: int) -> None:
    event = {"index": len(gamestate.book.events), "type": "spinMultiplier", "multiplier": spin_multiplier}
    gamestate.book.add_event(event)

def scatter_pay_event(gamestate, count: int, payout: float) -> None:
    event = {"index": len(gamestate.book.events), "type": "scatterPay", "count": count, "payout": int(round(payout * 100))}
    gamestate.book.add_event(event)

def bonus_trigger_event(gamestate, tier: str, scatter_count: int) -> None:
    event = {"index": len(gamestate.book.events), "type": "bonusTrigger", "tier": tier, "scatterCount": scatter_count}
    gamestate.book.add_event(event)

def bonus_start_event(gamestate, tier: str, spins: int, wild_reels: dict[int, int]) -> None:
    event = {
        "index": len(gamestate.book.events), "type": "bonusStart", "tier": tier, "spins": spins,
        "wildReels": {str(k): v for k, v in wild_reels.items()},
    }
    gamestate.book.add_event(event)

def five_wilds_event(gamestate) -> None:
    """All 5 reels Wild: the round pays the max win and ends."""
    event = {"index": len(gamestate.book.events), "type": "fiveWilds", "amount": int(round(gamestate.config.wincap * 100))}
    gamestate.book.add_event(event)

def wheel_spin_event(gamestate, result: str, payload: dict) -> None:
    event = {"index": len(gamestate.book.events), "type": "wheelSpin", "result": result, **payload}
    gamestate.book.add_event(event)

def sticky_wild_update_event(gamestate, wild_reels: dict[int, int]) -> None:
    event = {"index": len(gamestate.book.events), "type": "stickyWildUpdate", "wildReels": {str(k): v for k, v in wild_reels.items()}}
    gamestate.book.add_event(event)

def golden_case_reveal_event(gamestate, letters_landed: int, win: bool) -> None:
    event = {"index": len(gamestate.book.events), "type": "goldenCaseReveal", "lettersLanded": letters_landed, "maxWin": win}
    gamestate.book.add_event(event)
