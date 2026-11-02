"""Family-level splits (FR-TASK-5): pilot (stratified basic/advanced), main, heldout ⊂ main."""
from __future__ import annotations

import math
import random

from prl.config import PATHS, write_json
from prl.tasks import instances as INS
from prl.tasks.verina import Family


def make_splits(fams: list[Family], pilot_n: int, heldout_frac: float, seed: int) -> dict[str, list[str]]:
    elig = sorted((f for f in fams if f.eligible), key=lambda f: f.family_id)
    rng = random.Random(seed)
    basic = [f.family_id for f in elig if f.tier == "basic"]
    adv = [f.family_id for f in elig if f.tier == "advanced"]
    rng.shuffle(basic)
    rng.shuffle(adv)
    n_b = round(pilot_n * len(basic) / max(1, len(basic) + len(adv)))
    pilot = sorted(basic[:n_b] + adv[: pilot_n - n_b])
    main = sorted(set(basic[n_b:] + adv[pilot_n - n_b:]))
    rng2 = random.Random(seed + 1)
    m2 = list(main)
    rng2.shuffle(m2)
    held = sorted(m2[: math.ceil(heldout_frac * len(main))])
    confirm = sorted(set(main) - set(held))
    return {"pilot": pilot, "main": confirm, "heldout": held, "seed": [seed]}


def apply_splits(splits: dict[str, list[str]]) -> dict[str, int]:
    write_json(PATHS.data / "splits.json", splits)
    where = {fid: s for s in ("pilot", "main", "heldout") for fid in splits[s]}
    counts: dict[str, int] = {}
    for inst in INS.load_all():
        inst.split = where.get(inst.family_id, "excluded")
        INS.save(inst)
        counts[inst.split] = counts.get(inst.split, 0) + 1
    return counts
