#!/usr/bin/env python3
"""
test_floor_test.py - proves floor_test.py gives the right verdict on data with a
known answer, including the case that matters most: an instrument that invents
interactions.

    python test_floor_test.py

HOW THE DATA IS BUILT
---------------------
Each pair is (name, kind, true interaction, noise). With noise 0 the interaction
of every item is exactly the true value, so single-case verdict tests are
deterministic and cannot pass or fail by luck. Noisy nulls are tested separately,
as a RATE over many seeds, which is the only honest way to test a false alarm.

The first version of these tests used one noisy seed per verdict and caught a
real flaw instead of passing: floors and audited pairs were corrected together,
so strong audited effects made the correction more lenient for the floors and a
floor with a true interaction of zero was flagged. See section 3.

Sections 6 to 9 cover what Paper 3's answer-probability channel taught on real
data: a ceiling and a heavy tail make the two tests disagree (7), floors can
cancel across difficulty strata (8), and a negative interaction means
compounding only when the singles are costs (9).
"""

import csv
import json
import math
import os
import random
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import floor_test as FT      # noqa: E402

PASS, FAIL = [], []


def ok(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'ok  ' if cond else 'FAIL'}] {name}"
          f"{('  ' + detail) if detail else ''}")


def write(path, pairs, n_items=200, seed=1, binary=False):
    """pairs: (name, kind, true interaction, noise) tuples."""
    rng = random.Random(seed)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FT.REQUIRED)
        for name, kind, inter, noise in pairs:
            for i in range(n_items):
                if binary:
                    p = [min(.95, max(.05, 0.55 + x)) for x in
                         (0.0, -0.05, -0.05, -0.10 + inter)]
                    cells = [1 if rng.random() < q else 0 for q in p]
                else:
                    base = rng.gauss(0, 1)
                    e = [rng.gauss(0, noise) if noise else 0.0
                         for _ in range(4)]
                    cells = [base + e[0], base - 0.3 + e[1], base - 0.3 + e[2],
                             base - 0.6 + inter + e[3]]
                w.writerow([name, kind, f"item{i}"] + cells)


def run(pairs, **kw):
    path = os.path.join(tempfile.mkdtemp(), "data.csv")
    write(path, pairs, **kw)
    return FT.analyse(FT.read(path)), path


EXACT_FLOORS = [("cycling_x_bread", "floor", 0.0, 0.0),
                ("dog_x_guitar", "floor", 0.0, 0.0),
                ("tea_x_books", "floor", 0.0, 0.0)]
NOISY_FLOORS = [("cycling_x_bread", "floor", 0.0, 0.3),
                ("dog_x_guitar", "floor", 0.0, 0.3),
                ("tea_x_books", "floor", 0.0, 0.3)]

# ==========================================================================
print("=" * 70)
print("1. STATISTICS")
print("=" * 70)
ok("signed rank: all zeros gives p = 1", FT.signed_rank_p([0] * 30) == 1.0)
ok("signed rank: a one-sided set is significant",
   FT.signed_rank_p([-1.0] * 40 + [0.2] * 2) < 0.001)
ok("signed rank: a symmetric set is not", FT.signed_rank_p([1, -1] * 25) > 0.5)
ok("signed rank: small n uses the exact sign test",
   abs(FT.signed_rank_p([1, 1, 1, 1, 1]) - 0.0625) < 1e-12)
adj = FT.bh([0.001, 0.02, 0.5])
ok("BH is monotone and never below raw p",
   adj == sorted(adj) and all(a >= b for a, b in zip(adj, [0.001, 0.02, 0.5])))
h = FT.holm([0.01, 0.04, 0.03])
ok("Holm on a hand-computed case", all(abs(a - b) < 1e-12 for a, b in
                                        zip(h, [0.03, 0.06, 0.06])), f"{h}")
ok("Holm is never more lenient than BH",
   all(x >= y for x, y in zip(FT.holm([0.001, 0.02, 0.03, 0.5]),
                              FT.bh([0.001, 0.02, 0.03, 0.5]))))
ok("MDE shrinks with n", FT.mde([1, -1] * 20) > FT.mde([1, -1] * 200))
ok("interaction arithmetic: (both - a) - (b - none)",
   FT.interaction((0.0, -1.0, -2.0, -2.5)) == (-2.5 + 1.0) - (-2.0 - 0.0))

# ==========================================================================
print()
print("=" * 70)
print("2. VERDICTS, deterministic")
print("=" * 70)
res, path = run(EXACT_FLOORS + [("reader_x_age", "social", -0.5, 0.3),
                                ("adhd_x_deaf", "social", 0.0, 0.0)])
rows = {r["pair"]: r for r in res["rows"]}
ok("floors at exactly zero give CLEAN", res["verdict"] == "CLEAN")
ok("a real -0.5 interaction is found",
   abs(rows["reader_x_age"]["interaction"] + 0.5) < 0.1
   and rows["reader_x_age"]["p_adjusted"] < 0.05,
   f"{rows['reader_x_age']['interaction']:+.3f}")
ok("an audited pair at exactly zero stays null",
   rows["adhd_x_deaf"]["p_adjusted"] >= 0.05)
ok("floors use Holm on either test, audited pairs BH on both tests",
   all(r["correction"] == "holm, either test" for r in res["rows"]
       if r["kind"] == "floor")
   and all(r["correction"] == "bh, both tests" for r in res["rows"]
           if r["kind"] == "social"))
ok("the real interaction is claimed and labelled as compounding",
   rows["reader_x_age"]["claimed"]
   and rows["reader_x_age"]["direction"].startswith("compounds"),
   rows["reader_x_age"]["direction"])
ok("no warnings with three floors and enough items", not res["warnings"])
ok("exit code 0 when clean", FT.main([path]) == 0)

res, path = run(EXACT_FLOORS[:2] + [("tea_x_books", "floor", 0.6, 0.3),
                                    ("reader_x_age", "social", -0.5, 0.3)])
ok("ONE moving floor out of three gives CONTAMINATED",
   res["verdict"] == "CONTAMINATED" and res["floors_moving"] == ["tea_x_books"],
   f"{res['floors_moving']}")
ok("exit code 2 when contaminated", FT.main([path]) == 2)

res, _ = run(EXACT_FLOORS[:1] + [("reader_x_age", "social", 0.0, 0.3)])
ok("a single floor pair is warned about",
   any("only 1 floor" in w for w in res["warnings"]))
res, _ = run(EXACT_FLOORS + [("reader_x_age", "social", 0.0, 0.3)], n_items=8)
ok("too few items is warned about",
   any("little power" in w for w in res["warnings"]))
res, _ = run(EXACT_FLOORS + [("reader_x_age", "social", -0.25, 0.0)],
             binary=True, n_items=600)
ok("binary 0/1 outcomes are accepted", res["verdict"] in ("CLEAN",
                                                          "CONTAMINATED"))
json_path = os.path.join(tempfile.mkdtemp(), "report.json")
_, path = run(EXACT_FLOORS + [("reader_x_age", "social", -0.5, 0.3)])
FT.main([path, "--json", json_path])
ok("--json writes the verdict",
   json.load(open(json_path, encoding="utf-8"))["verdict"] == "CLEAN")

# ==========================================================================
print()
print("=" * 70)
print("3. THE FLAW THE FIRST VERSION HAD")
print("=" * 70)
print("   The same noisy floors, with and without strong audited effects")
print("   alongside. A floor's adjusted p must not depend on what else the")
print("   audit found.")
with_strong, _ = run(NOISY_FLOORS + [("a", "social", -0.9, 0.3),
                                     ("b", "social", -0.9, 0.3)], seed=5)
without, _ = run(NOISY_FLOORS + [("a", "social", 0.0, 0.3),
                                 ("b", "social", 0.0, 0.3)], seed=5)
f1 = {r["pair"]: r["p_adjusted_rank"] for r in with_strong["rows"]
      if r["kind"] == "floor"}
f2 = {r["pair"]: r["p_adjusted_rank"] for r in without["rows"]
      if r["kind"] == "floor"}
ok("floor correction is independent of the audited results", f1 == f2,
   "under one joint BH the strong audited effects made floors easier to flag")
joint = FT.bh([r["p_rank"] for r in with_strong["rows"]])
joint_floor = [a for a, r in zip(joint, with_strong["rows"])
               if r["kind"] == "floor"]
ok("and the joint correction really was more lenient on these floors",
   min(joint_floor) < min(f1.values()),
   f"joint BH {min(joint_floor):.4f} against Holm {min(f1.values()):.4f}")

# ==========================================================================
print()
print("=" * 70)
print("4. BAD INPUT IS REFUSED, NOT GUESSED AT")
print("=" * 70)


def bad(rows_, header=None):
    p = os.path.join(tempfile.mkdtemp(), "bad.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header or FT.REQUIRED)
        w.writerows(rows_)
    return FT.main([p])


ok("no floor pair: exit 1", bad([["x", "social", "i1", 0, 0, 0, 0]]) == 1)
ok("unknown kind: exit 1", bad([["x", "neutral", "i1", 0, 0, 0, 0]]) == 1)
ok("a non-number cell: exit 1",
   bad([["x", "floor", "i1", 0, "high", 0, 0]]) == 1)
ok("a duplicated item: exit 1",
   bad([["x", "floor", "i1", 0, 0, 0, 0],
        ["x", "floor", "i1", 1, 1, 1, 1]]) == 1)
ok("a missing column: exit 1",
   bad([["x", "floor", "i1", 0, 0, 0]], header=FT.REQUIRED[:-1]) == 1)
ok("a missing file: exit 1", FT.main(["does_not_exist.csv"]) == 1)

# ==========================================================================
print()
print("=" * 70)
print("5. FALSE ALARMS, as a rate over many seeds")
print("=" * 70)
FT.PERMUTATIONS = 1000
FT.BOOTSTRAP = 50
trials = 150
alarms = alarms_any = 0
for s in range(trials):
    res, _ = run(NOISY_FLOORS + [("reader_x_age", "social", -0.5, 0.3)],
                 seed=1000 + s)
    alarms += res["verdict"] == "CONTAMINATED"
    alarms_any += res["verdict"] != "CLEAN"
ok("three null floors are flagged at about the nominal 5 percent",
   alarms / trials <= 0.075, f"{alarms} of {trials} = {alarms / trials:.1%}")
ok("overall and within strata, one family: false alarm still near nominal",
   alarms_any / trials <= 0.075,
   f"{alarms_any} of {trials} = {alarms_any / trials:.1%}")

# ==========================================================================
print()
print("=" * 70)
print("6. THE TWO NEW STATISTICS")
print("=" * 70)
ok("sign flip: twelve identical positives, exact p is 2/4096",
   FT.sign_flip_p([1.0] * 12, reps=20000) < 0.002,
   f"{FT.sign_flip_p([1.0] * 12, reps=20000):.5f}")
ok("sign flip: a mean of exactly zero gives p = 1",
   FT.sign_flip_p([1.0, -1.0] * 15) == 1.0)
rng6 = random.Random(3)
sym = [rng6.gauss(0, 1) for _ in range(101)]
# reference: for 101 Gaussian values the sign-flip distribution of the sum is
# very close to normal with variance sum(d^2); checked once against a plain
# loop at 40,000 flips (0.1162 both, normal 0.1161)
normal_p = math.erfc(abs(sum(sym)) / math.sqrt(2 * sum(x * x for x in sym)))
fast_p = FT.sign_flip_p(sym, reps=20000)
ok("sign flip: the table method matches the normal reference",
   abs(normal_p - fast_p) < 0.015, f"table {fast_p:.4f}, normal {normal_p:.4f}")
ok("sign flip handles a length that is not a multiple of eight",
   0 < FT.sign_flip_p([0.5] * 13 + [-0.1], reps=2000) < 0.01)
ok("Hodges-Lehmann of 1, 2, 3 is 2", FT.hodges_lehmann([1.0, 2.0, 3.0]) == 2.0)
ok("Hodges-Lehmann is not moved by one wild value",
   abs(FT.hodges_lehmann([0.1] * 30 + [50.0]) - 0.1) < 1e-9)


# ==========================================================================
def write_cells(path, pairs, n_items=600, seed=1):
    """pairs: (name, kind, function(item_index, rng) -> 4 cells)."""
    rng = random.Random(seed)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FT.REQUIRED)
        for name, kind, fn in pairs:
            for i in range(n_items):
                w.writerow([name, kind, f"item{i}"] + list(fn(i, rng)))
    return path


def t3(rng):
    """Student t with 3 degrees of freedom, standard library only."""
    z = rng.gauss(0, 1)
    chi = sum(rng.gauss(0, 1) ** 2 for _ in range(3))
    return z / math.sqrt(chi / 3)


def ceiling(extra=lambda rng: 0.0):
    """45 percent of items at the ceiling; the rest heavy tailed."""
    def fn(i, rng):
        if (i * 7919) % 100 < 45:
            return (0.0, 0.0, 0.0, 0.0)
        return (0.0, 0.0, 0.0, t3(rng) * 0.35 + extra(rng))
    return fn


def skew(rng):
    return 3.0 if rng.random() < 0.12 else -0.15


print()
print("=" * 70)
print("7. A CEILING AND A HEAVY TAIL, where the two tests disagree")
print("=" * 70)
FT.PERMUTATIONS = 4000
found = None
for s in range(40):
    p = write_cells(os.path.join(tempfile.mkdtemp(), "c.csv"),
                    [("f_skew", "floor", ceiling(skew)),
                     ("f_null1", "floor", ceiling()),
                     ("f_null2", "floor", ceiling())], seed=s)
    r7 = FT.analyse(FT.read(p))
    fs = next(x for x in r7["rows"] if x["pair"] == "f_skew")
    if fs["p_adjusted_rank"] >= 0.05 and fs["p_adjusted"] < 0.05:
        found = (s, r7, fs)
        break
ok("a skewed floor exists that the signed-rank test misses and the mean "
   "test catches", found is not None)
if found:
    s7, r7, fs = found
    ok("and the verdict is CONTAMINATED", r7["verdict"] == "CONTAMINATED",
       f"Holm rank {fs['p_adjusted_rank']:.3g}, mean {fs['p_adjusted_mean']:.3g}")
    p = write_cells(os.path.join(tempfile.mkdtemp(), "c.csv"),
                    [("f1", "floor", ceiling()), ("f2", "floor", ceiling()),
                     ("f3", "floor", ceiling()),
                     ("s_skew", "social", ceiling(skew))], seed=s7)
    r7b = FT.analyse(FT.read(p))
    ss = next(x for x in r7b["rows"] if x["pair"] == "s_skew")
    ok("the same skew as an audited pair is NOT claimed",
       not ss["claimed"],
       f"mean {ss['interaction']:+.3f}, HL {ss['hl']:+.3f}, "
       f"p rank {ss['p_rank']:.3g}, p mean {ss['p_mean']:.3g}")


def shifted(shift_hard, shift_easy, singles=(0.0, 0.0)):
    """Items alternate easy and hard; the both cell moves by stratum."""
    def fn(i, rng):
        base = 5.0 if i % 2 == 0 else -5.0
        e = [rng.gauss(0, 0.1) for _ in range(4)]
        inter = shift_easy if i % 2 == 0 else shift_hard
        return (base + e[0], base + singles[0] + e[1],
                base + singles[1] + e[2],
                base + singles[0] + singles[1] + inter + e[3])
    return fn


print()
print("=" * 70)
print("8. FLOORS THAT CANCEL ACROSS STRATA")
print("=" * 70)
p = write_cells(os.path.join(tempfile.mkdtemp(), "s.csv"),
                [("f_cancel", "floor", shifted(+0.6, -0.6)),
                 ("f_null1", "floor", shifted(0, 0)),
                 ("f_null2", "floor", shifted(0, 0)),
                 ("s_a", "social", shifted(0, 0))], seed=4)
r8 = FT.analyse(FT.read(p))
fc = next(x for x in r8["rows"] if x["pair"] == "f_cancel")
ok("a floor of +0.6 on hard items and -0.6 on easy ones is quiet overall",
   fc["p_adjusted"] >= 0.05, f"mean {fc['interaction']:+.3f}")
ok("the verdict is CLEAN IN AGGREGATE ONLY",
   r8["verdict"] == "CLEAN IN AGGREGATE ONLY",
   ", ".join(r8["floors_moving_within_strata"]))
ok("and the exit code is 2", FT.main([p]) == 2)
ok("the strata separate the easy and the hard halves",
   {x["stratum"] for x in r8["strata"]
                if x["pair"] == "f_cancel" and x["p_adjusted"] < 0.05}
   >= {"lowest", "highest"})
p = write_cells(os.path.join(tempfile.mkdtemp(), "s.csv"),
                [("f1", "floor", shifted(0, 0)), ("f2", "floor", shifted(0, 0)),
                 ("f3", "floor", shifted(0, 0))], seed=5)
ok("the same design with no movement is CLEAN",
   FT.analyse(FT.read(p))["verdict"] == "CLEAN")
few = os.path.join(tempfile.mkdtemp(), "l.csv")
with open(few, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(FT.REQUIRED)
    rng8 = random.Random(1)
    for pair in ("f1", "f2", "f3"):
        for i in range(40):
            b = rng8.gauss(0, 1)
            w.writerow([pair, "floor", f"item{i}", b, b, b, b])
r8c = FT.analyse(FT.read(few))
ok("too few items for three strata: the check is skipped, with a warning",
   not r8c["strata"]
   and any("stratified floor check not run" in x for x in r8c["warnings"]))

# The bug the first stratified version had, on the shape of real data: binary
# outcomes, many pairs, every pair sharing the same neutral cell per item.
# Ordering items by the OTHER pairs selected on this pair's own "none" and
# flagged null floors. Ordered by the pair's own four cells, it must not.
FT.PERMUTATIONS = 1000


def shared_none_file(seed, n_items=600, n_social=8):
    rng = random.Random(seed)
    diff = [rng.random() for _ in range(n_items)]
    none = [1 if rng.random() < diff[i] else 0 for i in range(n_items)]
    path = os.path.join(tempfile.mkdtemp(), "b.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FT.REQUIRED)
        names = [(f"floor{k}", "floor") for k in range(3)] + \
                [(f"social{k}", "social") for k in range(n_social)]
        for name, kind in names:
            for i in range(n_items):
                draw = [1 if rng.random() < diff[i] else 0 for _ in range(3)]
                w.writerow([name, kind, f"T{i:03d}", none[i]] + draw)
    return path


def others_key_alarm(data):
    """The first version's ordering, kept here only to show it was biased."""
    saved = FT.stratified_floors

    def by_others(data_, floors):
        rows_, skipped_ = [], []
        for fl in floors:
            own = data_[fl["pair"]]["items"]
            key = {it: FT.mean([v for p, e in data_.items() if p != fl["pair"]
                                and it in e["items"] for v in e["items"][it]])
                   for it in own}
            ordered = sorted(key, key=lambda i: (key[i], i))
            size = len(ordered) // 3
            for s in range(3):
                part = ordered[s * size:] if s == 2 else \
                    ordered[s * size:(s + 1) * size]
                r_ = FT.test_pair([FT.interaction(own[i]) for i in part])
                r_.update({"pair": fl["pair"], "stratum": str(s)})
                rows_.append(r_)
        return rows_, skipped_
    FT.stratified_floors = by_others
    try:
        return FT.analyse(data)["verdict"] != "CLEAN"
    finally:
        FT.stratified_floors = saved


FT.PERMUTATIONS = 500
seeds8 = 30
new_alarms = old_alarms = 0
for s in range(seeds8):
    data8 = FT.read(shared_none_file(300 + s))
    new_alarms += FT.analyse(data8)["verdict"] != "CLEAN"
    if s < 6:
        old_alarms += others_key_alarm(data8)
ok("shared neutral cell, null floors: ordering by the other pairs WAS biased",
   old_alarms >= 5, f"{old_alarms} of 6 falsely flagged")
ok("ordering by the pair's own cells is not",
   new_alarms / seeds8 <= 0.10, f"{new_alarms} of {seeds8} falsely flagged")
FT.PERMUTATIONS = 4000
FT.BOOTSTRAP = 1000

print()
print("=" * 70)
print("9. WHAT A SIGN MEANS")
print("=" * 70)
p = write_cells(os.path.join(tempfile.mkdtemp(), "d.csv"),
                [("f1", "floor", shifted(0, 0)), ("f2", "floor", shifted(0, 0)),
                 ("f3", "floor", shifted(0, 0)),
                 ("two_costs", "social", shifted(-0.4, -0.4, (-0.5, -0.5))),
                 ("two_benefits", "social", shifted(-0.4, -0.4, (+0.5, +0.5))),
                 ("costs_add_less", "social", shifted(+0.4, +0.4,
                                                      (-0.5, -0.5))),
                 ("mixed", "social", shifted(-0.4, -0.4, (-0.5, +0.5)))],
                seed=6)
r9 = {x["pair"]: x for x in FT.analyse(FT.read(p))["rows"]}
ok("two costs, negative interaction: compounds",
   r9["two_costs"]["direction"].startswith("compounds"))
ok("two benefits, negative interaction: benefit does not add",
   r9["two_benefits"]["direction"] == "benefit does not add",
   "what Paper 3 found on qwen")
ok("two costs, positive interaction: cost does not add",
   r9["costs_add_less"]["direction"] == "cost does not add")
ok("singles in opposite directions: no direction label",
   r9["mixed"]["direction"].startswith("singles point"))

print()
print("=" * 70)
print("10. BINARY OUTCOMES, where most differences are exactly zero")
print("=" * 70)
FT.PERMUTATIONS = 4000
bin_path = os.path.join(tempfile.mkdtemp(), "bin.csv")
with open(bin_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(FT.REQUIRED)
    for name in ("f1", "f2", "f3"):
        for i in range(600):
            w.writerow([name, "floor", f"T{i}", 1, 1, 1, 1])
    for i in range(600):
        # 70 items one step better, 30 one step worse, 500 unchanged
        both = 1 if i < 70 else (-1 if i < 100 else 0)
        w.writerow(["stated_x_stated", "social", f"T{i}", 0, 0, 0, both])
r10 = {x["pair"]: x for x in FT.analyse(FT.read(bin_path))["rows"]}
s10 = r10["stated_x_stated"]
ok("a real effect on mostly-zero differences is claimed",
   s10["claimed"] and s10["hl"] == 0,
   f"mean {s10['interaction']:+.3f}, HL {s10['hl']:+.1f}, rank direction "
   f"{s10['rank_dir']:+d}: a Hodges-Lehmann rule would have dropped it")
ok("rank_direction on hand cases",
   FT.rank_direction([0, 0, 1, 2, -1]) == 1
   and FT.rank_direction([0, 0]) == 0 and FT.rank_direction([1, -1]) == 0)
FT.PERMUTATIONS = 10000

# ==========================================================================
print()
print("=" * 70)
print(f"{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    for f in FAIL:
        print(f"  FAILED: {f}")
    sys.exit(1)
print("floor_test.py gives the right verdicts.")
print("=" * 70)
