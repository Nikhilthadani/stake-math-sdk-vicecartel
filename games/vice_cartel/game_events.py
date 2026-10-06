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

def mystery_trigger_event(gamestate, outcome: str) -> None:
    event = {"index": len(gamestate.book.events), "type": "mysteryTrigger", "outcome": outcome}
    gamestate.book.add_event(event)

def wheel_spin_event(gamestate, result: str, payload: dict) -> None:
    event = {"index": len(gamestate.book.events), "type": "wheelSpin", "result": result, **payload}
    gamestate.book.add_event(event)

def sticky_wild_update_event(gamestate, wild_reels: dict[int, int]) -> None:
    event = {"index": len(gamestate.book.events), "type": "stickyWildUpdate", "wildReels": {str(k): v for k, v in wild_reels.items()}}
    gamestate.book.add_event(event)

def survival_life_event(gamestate, lives_remaining: int, lost: bool) -> None:
    event = {"index": len(gamestate.book.events), "type": "survivalLife", "lives": lives_remaining, "lost": lost}
    gamestate.book.add_event(event)

def bonus_choice_event(gamestate, mode: str) -> None:
    event = {"index": len(gamestate.book.events), "type": "bonusChoice", "mode": mode}
    gamestate.book.add_event(event)

def golden_case_reveal_event(gamestate, letters_landed: int, win: bool) -> None:
    event = {"index": len(gamestate.book.events), "type": "goldenCaseReveal", "lettersLanded": letters_landed, "maxWin": win}
    gamestate.book.add_event(event)
