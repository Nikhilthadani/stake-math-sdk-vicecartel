"""Pick one real published book per frontend scenario into frontend/sample_books/."""

import io
import json
import os
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISH = os.path.join(HERE, "..", "library", "publish_files")
OUT = os.path.join(HERE, "sample_books")


def types(book):
    return [e["type"] for e in book["events"]]


def wheel(book, result, empty=None):
    for e in book["events"]:
        if e["type"] == "wheelSpin" and e["result"] == result:
            if empty is None or empty == (len(e) == 3):
                return True
    return False


def tier(book):
    for e in book["events"]:
        if e["type"] in ("bonusTrigger", "bonusStart"):
            return e["tier"]
    return None


# scenario -> (mode, cheap substring prefilter, predicate on parsed book)
SCENARIOS = {
    "base_no_win": ("base", None, lambda b: b["payoutMultiplier"] == 0),
    "base_line_win": ("base", "winInfo", lambda b: "wildReel" not in types(b) and "scatterPay" not in types(b)),
    "base_wild_multiplier_win": ("base", "spinMultiplier", lambda b: "winInfo" in types(b) and "bonusTrigger" not in types(b)),
    "base_five_wilds_max_win": ("base", "fiveWilds", lambda b: True),
    "base_bonus_normal": ("base", '"normal_bonus"', lambda b: tier(b) == "normal_bonus" and "wheelSpin" in types(b)),
    "base_bonus_super": ("base", '"super_bonus"', lambda b: tier(b) == "super_bonus" and "wheelSpin" in types(b)),
    "base_bonus_hidden": ("base", '"hidden_bonus"', lambda b: tier(b) == "hidden_bonus" and "wheelSpin" in types(b)),
    "base_bonus_super_hidden": ("base", '"super_hidden_bonus"', lambda b: tier(b) == "super_hidden_bonus" and "wheelSpin" in types(b)),
    "base_bonus_wheel_red": ("base", '"RED"', lambda b: wheel(b, "RED")),
    "base_bonus_wheel_blue": ("base", '"BLUE"', lambda b: wheel(b, "BLUE", empty=False)),
    "base_bonus_wheel_blue_no_wild": ("base", '"BLUE"', lambda b: wheel(b, "BLUE", empty=True)),
    "base_bonus_wheel_yellow": ("base", '"YELLOW"', lambda b: wheel(b, "YELLOW")),
    "base_bonus_wheel_max_win": ("base", '"MAX_WIN"', lambda b: wheel(b, "MAX_WIN")),
    "base_bonus_wincap_by_wins": ("base", '"wincap"', lambda b: "bonusTrigger" in types(b) and not wheel(b, "MAX_WIN")),
    "extra_chance_bonus": ("extra_chance", "bonusTrigger", lambda b: "wheelSpin" in types(b)),
    "bonus_normal_buy": ("bonus_normal", "wheelSpin", lambda b: b["payoutMultiplier"] > 0),
    "bonus_super_buy": ("bonus_super", "wheelSpin", lambda b: b["payoutMultiplier"] > 0),
    "min2wild_win": ("min2wild", "winInfo", lambda b: "fiveWilds" not in types(b)),
    "min2wild_five_wilds_max_win": ("min2wild", "fiveWilds", lambda b: True),
    "golden_case_win": ("golden_case", '"maxWin": true', lambda b: True),
    "golden_case_lose": ("golden_case", '"maxWin": false', lambda b: True),
}

# a bonus sample should stay readable: skip very long rounds when possible
MAX_LINE_CHARS = 60_000


def main():
    os.makedirs(OUT, exist_ok=True)
    found = {}
    for mode in dict.fromkeys(m for m, _, _ in SCENARIOS.values()):
        todo = {k: v for k, v in SCENARIOS.items() if v[0] == mode}
        fallback = {}
        path = os.path.join(PUBLISH, f"books_{mode}.jsonl.zst")
        with open(path, "rb") as fh:
            reader = io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
            for line in reader:
                hits = [k for k, (_, sub, _) in todo.items() if k not in found and (sub is None or sub in line)]
                if not hits:
                    continue
                book = json.loads(line)
                for k in hits:
                    if todo[k][2](book):
                        if len(line) <= MAX_LINE_CHARS:
                            found[k] = book
                        else:
                            fallback.setdefault(k, book)
                if all(k in found for k in todo):
                    break
        for k in todo:
            if k not in found and k in fallback:
                found[k] = fallback[k]
        print(mode, "->", [k for k in todo if k in found], "missing:", [k for k in todo if k not in found])

    index = {}
    for name, book in found.items():
        with open(os.path.join(OUT, f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump(book, f, indent=2)
        index[name] = {"mode": SCENARIOS[name][0], "bookId": book["id"], "payoutMultiplier": book["payoutMultiplier"],
                       "eventTypes": sorted(set(types(book)))}
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


if __name__ == "__main__":
    main()
