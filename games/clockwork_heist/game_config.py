"""Clockwork Heist configuration for Stake Engine.

Ports engine-clockwork: every number comes from `game_config.json`, a copy of
`engine-clockwork/src/config/game_config.json`. Keep the two files identical.

5 reels x 4 rows, 40 left-to-right paylines, wilds (WD) carry 2x/3x/5x
multipliers that add up on a line, 3 scatters (SC) trigger 8 free spins.
Modes: base (1x), bonus buy (100x), max win or nothing (100x: the Sticky Wild
Vault hold & respin; a full grid of Vault Keys pays 25,000x, otherwise the sum of
the key multipliers, at least 20x).
"""

import json
import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

GAME_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_config.json")

WILD = "WD"
SCATTER = "SC"
NUM_REELS = 5

# engine reel set name -> SDK reel id
REEL_IDS = {"base": "BR0", "free": "FR0", "buy": "BUY"}

# Share of mwon books that fill the grid (more distinct jackpot rounds); the lookup
# weights, not this share, carry the jackpot probability (run.py `set_mwon_weights`)
MWON_JACKPOT_BOOK_SHARE = 0.01

# A Vault Key lands when `random() < p`; `p` is limited to the engine's integer draw scale
MWON_PROBABILITY_DECIMALS = 9


def load_engine_config(path: str = GAME_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="UTF-8") as file:
        return json.load(file)


class GameConfig(Config):
    """Clockwork Heist configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        raw = load_engine_config()

        self.game_id = "clockwork_heist"
        self.provider_number = 0
        self.provider_name = "vicecartel"
        self.game_name = "clockwork_heist"
        self.working_name = raw["game"]
        self.win_type = "lines"
        # Published RTP of every mode (lookup weights are tilted onto it by run.py); band is 96.0-96.7%
        self.rtp = 0.9635
        self.wincap = float(raw["max_win"])
        self.construct_paths()

        # Game dimensions
        self.num_reels = NUM_REELS
        self.num_rows = [raw["rows"]] * self.num_reels

        # Paytable in multiples of total bet: {(count, symbol): pay}
        self.paytable = {
            (int(count), sym): float(pay) for sym, pays in raw["pays"].items() for count, pay in pays.items()
        }

        # 0-based keys keep `lineIndex` identical to engine-clockwork
        self.paylines = {i: list(line) for i, line in enumerate(raw["lines"])}

        # No padding rows: board rows stay 0..3 like the engine response
        self.include_padding = False
        self.special_symbols = {"wild": [WILD], "scatter": [SCATTER], "multiplier": [WILD]}

        # Base: 3 scatters (reels 1, 3, 5) -> 8 spins. Free reels hold no scatter;
        # free spins are only added by the gold meter, never by a retrigger.
        self.freespin_triggers = {
            self.basegame_type: {3: raw["free_spins"]["initial_spins"]},
            self.freegame_type: {99: 0},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: 99,
        }

        # Wild multiplier value -> weight, drawn for every newly landed wild (base and free)
        self.wild_mult_weights = {int(value): weight for value, weight in raw["wild_mult_weights"].items()}

        self.free_spins = {
            "initial_spins": raw["free_spins"]["initial_spins"],
            "min_award": float(raw["free_spins"]["min_award"]),
            "keys_per_award": raw["free_spins"]["extra"]["keys_per_award"],
            "spins_per_award": raw["free_spins"]["extra"]["spins_per_award"],
        }
        self.bonus_buy_price = float(raw["bonus_buy"]["price"])
        mwon = raw["max_win_or_nothing"]
        self.max_win_or_nothing = {
            "price": float(mwon["price"]),
            "start_keys": mwon["start_keys"],
            "respins": mwon["respins"],
            "land_probability": mwon["land_probability"],
            "mult_weights": {int(value): weight for value, weight in mwon["mult_weights"].items()},
            "min_award": float(mwon["min_award"]),
            "win_amount": float(mwon["win_amount"]),
        }

        # Reels: strips have different lengths per reel, so they load from JSON, not CSV
        self.reels = {REEL_IDS[name]: [list(strip) for strip in strips] for name, strips in raw["reels"].items()}
        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        self.validate(raw)
        self.bet_modes = self.build_bet_modes()

    def validate(self, raw: dict) -> None:
        """Same guards as engine-clockwork `parseGameConfig`."""
        rows = raw["rows"]
        for index, line in self.paylines.items():
            assert len(line) == self.num_reels, f"Line {index} needs {self.num_reels} rows"
            assert all(0 <= row < rows for row in line), f"Line {index} has a row outside 0..{rows - 1}"

        self.get_paying_symbols()
        self.get_special_symbol_names()
        self.all_valid_sym_names = set(self.paying_symbol_names) | set(self.special_sybol_names)
        for reel_id, strips in self.reels.items():
            assert len(strips) == self.num_reels, f"{reel_id} needs {self.num_reels} strips"
            self.validate_reel_symbols(strips)
            assert WILD not in strips[0], f"{reel_id} reel 1 holds {WILD}; line evaluation requires a wild-free reel 1"

        for engine_name, reel_id in REEL_IDS.items():
            counts = raw["reel_build"]["counts"][engine_name]
            for r, strip in enumerate(self.reels[reel_id]):
                want = {sym: n for sym, n in counts[str(r + 1)].items() if n > 0}
                got = {}
                for sym in strip:
                    got[sym] = got.get(sym, 0) + 1
                assert got == want, f"{reel_id} reel {r + 1} symbol counts differ from reel_build"

        self.validate_buy_reels(rows)

        assert self.free_spins["min_award"] <= self.wincap, "free_spins.min_award exceeds max_win"
        mwon = self.max_win_or_nothing
        assert mwon["win_amount"] <= self.wincap, "max_win_or_nothing.win_amount exceeds max_win"
        assert mwon["start_keys"] < self.num_reels * rows, "max_win_or_nothing.start_keys must leave at least one empty cell"
        p = mwon["land_probability"]
        assert 0 < p < 1 and round(p, MWON_PROBABILITY_DECIMALS) == p, (
            f"max_win_or_nothing.land_probability needs 0 < p < 1 and at most {MWON_PROBABILITY_DECIMALS} decimals"
        )

    def validate_buy_reels(self, rows: int) -> None:
        """Every BUY screen must trigger and pay nothing (engine `playBuyRound` guard, proven for all stops).

        Exactly one SC in every window of reels 1, 3, 5 and none on reels 2, 4 gives exactly 3 scatters;
        it also makes the SDK's forced-scatter draw pick every BUY screen with its natural probability.
        No WD and no symbol shared by reels 1 and 2 means no line can reach 3 of a kind.
        """
        strips = self.reels["BUY"]
        scatter_reels = {0, 2, 4}
        for r, strip in enumerate(strips):
            n = len(strip)
            per_window = {sum(strip[(p + k) % n] == SCATTER for k in range(rows)) for p in range(n)}
            want = {1} if r in scatter_reels else {0}
            assert per_window == want, f"BUY reel {r + 1}: scatters per window {per_window}, need {want}"
            assert WILD not in strip, f"BUY reel {r + 1} holds {WILD}"
        assert not set(strips[0]) & set(strips[1]), "BUY reels 1 and 2 share a symbol, so the trigger spin can pay"

    def build_bet_modes(self) -> list:
        """Skeleton distributions; quotas are tuned in game_optimization.py.

        No `wincap` criteria in base/bonus: with at most 14 free spins and no
        retrigger, 25,000x is unreachable there (PAR "Assumptions & Gaps" G-01;
        largest of 4M buys is 6,582x), so a forced-wincap book would never finish.
        """
        mult_values = {self.basegame_type: self.wild_mult_weights, self.freegame_type: self.wild_mult_weights}
        base_reels = {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}}
        buy_reels = {self.basegame_type: {"BUY": 1}, self.freegame_type: {"FR0": 1}}
        trigger = {min(self.freespin_triggers[self.basegame_type].keys()): 1}

        base_freegame = {"reel_weights": base_reels, "mult_values": mult_values, "scatter_triggers": trigger,
                         "force_wincap": False, "force_freegame": True}
        base_zero = {"reel_weights": base_reels, "mult_values": mult_values,
                     "force_wincap": False, "force_freegame": False}
        base_basegame = {"reel_weights": base_reels, "mult_values": mult_values,
                         "force_wincap": False, "force_freegame": False}

        buy_freegame = {"reel_weights": buy_reels, "mult_values": mult_values, "scatter_triggers": trigger,
                        "force_wincap": False, "force_freegame": True}

        return [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(criteria="freegame", quota=0.1, conditions=base_freegame),
                    Distribution(criteria="0", quota=0.4, win_criteria=0.0, conditions=base_zero),
                    Distribution(criteria="basegame", quota=0.5, conditions=base_basegame),
                ],
            ),
            BetMode(
                name="bonus",
                cost=self.bonus_buy_price,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="freegame", quota=1.0, conditions=buy_freegame),
                ],
            ),
            BetMode(
                name="mwon",
                cost=self.max_win_or_nothing["price"],
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                # The vault grid draws no reels (no `reel_weights`): keys come from max_win_or_nothing.
                # `wincap` = full grid; `basegame` = every other round (a full grid there is played again).
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=MWON_JACKPOT_BOOK_SHARE,
                        win_criteria=self.max_win_or_nothing["win_amount"],
                        conditions={"force_wincap": True},
                        required_distribution_conditions=[],
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=1 - MWON_JACKPOT_BOOK_SHARE,
                        conditions={},
                        required_distribution_conditions=[],
                    ),
                ],
            ),
        ]
