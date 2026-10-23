# Vice Cartel math v2.0 — reference model

Standalone, seeded reference implementation of the rebuilt Vice Cartel math. It is meant to be ported into `stake-math-sdk-vicecartel`; see `docs/CHANGE_REPORT.md` §3.

```
pip install numpy scipy pytest
python -m pytest -q tests                      # rules, determinism, engine vs simulator vs exact
python -m vice_cartel_math.calibrate           # re-solve bonus wheel parameters
python -m vice_cartel_math.validate            # full validation (~45 min on 2 cores)
python -m vice_cartel_math.report              # -> docs/VALIDATION_REPORT.md
```

Single round from a seed (what a book would contain):

```python
from vice_cartel_math import engine
r = engine.play("bonus_super", seed=42)
r.payout, r.events
```

Production book weighting: `vice_cartel_math/books.py`.

Docs: `docs/MATH_SPEC.md` (rules and numbers), `docs/VALIDATION_REPORT.md` (evidence), `docs/CHANGE_REPORT.md` (root causes, porting, open questions).
