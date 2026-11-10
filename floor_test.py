#!/usr/bin/env python3
"""
floor_test.py - does your bias audit measure people, or words?

    python floor_test.py results.csv
    python floor_test.py results.csv --json report.json

Exit codes, so it can sit in a pipeline:
    0   floor clean: interactions can be read
    2   floor contaminated, overall or within a difficulty stratum: this
        instrument cannot identify an interaction
    1   the input could not be used

No dependencies beyond the Python standard library.

THE PROBLEM
-----------
An audit that asks "do two characteristics together hurt a person more than
each one alone" compares four versions of the same case: neither, the first,
the second, and both. The interaction is (both - first) - (second - neither).

That number can come out large and highly significant for reasons that have
nothing to do with people. Many instruments that read a model's probabilities
respond to the combination of any two pieces of text, including two that mean
nothing socially. Such an instrument will report a compounding effect for every
pair you give it.

THE TEST
--------
Alongside the pairs you are auditing, build FLOOR pairs: two socially neutral
but distinctive details ("I cycle to work", "I bake my own bread"), inserted in
exactly the same positions and the same way. Their interaction should be zero.

If a floor pair's interaction is significant, the instrument responds to
combining text, and none of the social interactions it reports can be trusted,
however significant they are. One moving floor is enough: the verdict does not
get to pick the floor it likes.

The floors are corrected as their own family, family-wise (Holm), because the
question is whether ANY of them moves. The audited pairs are corrected among
themselves for false discoveries (Benjamini-Hochberg). Correcting the two
together would make a quiet floor easier to flag the more the audit finds.

TWO TESTS, ONE CONSERVATIVE RULE
--------------------------------
The reported interaction is a mean. The signed-rank test does not test a mean,
and on outcomes with a ceiling and a heavy tail the two disagree: in Paper 3 a
floor had a mean of +0.18 with an interval excluding zero and a signed-rank p
of 0.87, because almost half the items sat at the ceiling. So every pair is
tested twice, by signed rank and by a sign-flip permutation test on the mean:

    floor     moves if EITHER test rejects
    audited   counts only if BOTH reject, and the mean and the signed-rank
              statistic lean the same way

The direction check leans on the signed ranks rather than on the Hodges-Lehmann
estimate, which is still reported. On 0 or 1 outcomes most differences are
exactly zero, the estimate is then 0 for real effects too, and a rule built on
it would drop them.

Each half can only take a claim away.

FLOORS WITHIN DIFFICULTY STRATA
-------------------------------
A floor can be quiet on average because it moves one way on easy items and the
other way on hard ones. Paper 3 found exactly that. Each floor is therefore also
tested within thirds of its items, ordered by the mean of the floor's own four
cells. The interaction weighs those cells +1, -1, -1, +1 and the mean weighs
them equally, so the two are uncorrelated when the cells are equally noisy and
selecting on the mean does not bias the interaction. A floor that is quiet
overall and moves within a stratum gives the verdict CLEAN IN AGGREGATE ONLY,
and exit code 2.

The whole floor question is ONE family: every floor overall and within every
stratum, Holm across all of them per test, and Bonferroni across the two tests.
So the chance of calling a quiet instrument contaminated stays at 5 percent
however many ways the floor is looked at.

The first version ordered items by how the OTHER pairs scored instead, and it
was biased: pairs from one run share the same neutral cell, so the other pairs
carried this pair's own "none", which enters the interaction with +1. On real
binary data it flagged a floor that does not move. See the tests, section 8.

WHAT A SIGN MEANS
-----------------
A negative interaction is compounding harm only when both single effects are
costs. If both singles help, a negative interaction is a benefit that does not
add. The report labels each audited interaction by the direction of its
singles, measured as the mean of a - none and b - none.

INPUT
-----
A CSV with one row per pair and item:

    pair,kind,item,none,a,b,both

    pair   a name for the pair, e.g. screen_reader_x_age
    kind   social (a pair you are auditing) or floor (a neutral pair)
    item   the unit the four versions share: a task, a profile, a question.
    none, a, b, both
           the outcome for that item in each of the four versions, as numbers:
           0 or 1, a score, a log probability, anything, as long as all four
           cells use the same scale

Use at least three floor pairs. Fewer is reported as a warning, because one
neutral pair can itself be unusual.

WHAT IT DOES NOT DO
-------------------
It does not repair a contaminated instrument; nothing in the arithmetic can.
And it does not accept margins that were each measured against a shared
reference (for example "A against NONE" and "both against NONE" from a
two-option choice): differencing those is not an interaction, and a floor built
that way will move for purely arithmetic reasons. See DESIGN.md.
"""

import csv
import json
import math
import random
import sys

REQUIRED = ["pair", "kind", "item", "none", "a", "b", "both"]
MIN_FLOORS = 3
MIN_ITEMS = 20
ALPHA = 0.05
BOOTSTRAP = 1000
PERMUTATIONS = 10000
STRATA = 3
HL_MAX_PAIRS = 200000
SEED = 20260908


class InputError(ValueError):
    pass


def read(path):
    """Returns {pair: {"kind": kind, "items": {item: (none, a, b, both)}}}."""
    try:
        f = open(path, newline="", encoding="utf-8-sig")
    except OSError as e:
        raise InputError(f"cannot open {path}: {e}")
    with f:
        rd = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (rd.fieldnames or [])]
        if missing:
            raise InputError(f"missing columns: {', '.join(missing)}. "
                             f"Expected: {','.join(REQUIRED)}")
        data = {}
        for line, r in enumerate(rd, start=2):
            kind = (r["kind"] or "").strip().lower()
            if kind not in ("social", "floor"):
                raise InputError(f"line {line}: kind must be social or floor, "
                                 f"got {r['kind']!r}")
            try:
                vals = tuple(float(r[k]) for k in ("none", "a", "b", "both"))
            except (TypeError, ValueError):
                raise InputError(f"line {line}: none, a, b and both must all "
                                 f"be numbers")
            if any(math.isnan(v) or math.isinf(v) for v in vals):
                raise InputError(f"line {line}: a cell is NaN or infinite; "
                                 f"drop the item instead")
            pair = (r["pair"] or "").strip()
            item = (r["item"] or "").strip()
            if not pair or not item:
                raise InputError(f"line {line}: pair and item cannot be empty")
            entry = data.setdefault(pair, {"kind": kind, "items": {}})
            if entry["kind"] != kind:
                raise InputError(f"pair {pair} is marked both social and floor")
            if item in entry["items"]:
                raise InputError(f"line {line}: pair {pair} has item {item} "
                                 f"twice")
            entry["items"][item] = vals
    if not data:
        raise InputError("the file has no rows")
    return data


def interaction(vals):
    """(both - a) - (b - none), rounded to nine decimals.

    The rounding removes floating-point residue. Without it an item whose true
    interaction is exactly zero comes out as something like 1e-16 with a
    consistent sign, the signed-rank test counts every such item as a real
    difference, and a perfectly flat floor is flagged as moving. The unit tests
    caught this with floors built to be exactly zero.
    """
    none, a, b, both = vals
    return round((both - a) - (b - none), 9)


def mean(v):
    return sum(v) / len(v)


def mde(d):
    """95 percent half-width: the smallest interaction this data can see."""
    n = len(d)
    if n < 2:
        return float("nan")
    m = mean(d)
    return 1.96 * math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1) / n)


def boot_ci(d, reps=None, seed=SEED):
    reps = BOOTSTRAP if reps is None else reps
    rng = random.Random(seed)
    n = len(d)
    means = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n
                   for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps) - 1]


def signed_rank_p(d):
    """Two-sided Wilcoxon signed-rank, zeros dropped.

    Exact sign test below 10 nonzero values; normal approximation with tie
    correction and continuity correction above.
    """
    nz = [x for x in d if x != 0]
    n = len(nz)
    if n == 0:
        return 1.0
    if n < 10:
        pos = sum(1 for x in nz if x > 0)
        k = min(pos, n - pos)
        return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1))
                   / 2 ** n)
    order = sorted(nz, key=abs)
    ranks = [0.0] * n
    ties = 0.0
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(order[j + 1]) == abs(order[i]):
            j += 1
        t = j - i + 1
        ties += t ** 3 - t
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        i = j + 1
    w_plus = sum(r for r, x in zip(ranks, order) if x > 0)
    mu = n * (n + 1) / 4
    var = n * (n + 1) * (2 * n + 1) / 24 - ties / 48
    if var <= 0:
        return 1.0
    z = (abs(w_plus - mu) - 0.5) / math.sqrt(var)
    return min(1.0, math.erfc(max(z, 0.0) / math.sqrt(2)))


def sign_flip_p(d, reps=None, seed=SEED):
    """Two-sided paired permutation test on the mean.

    Under the null each difference is as likely to carry either sign. The sum
    of a random sign flip is 2 * (sum of the kept values) - (total), and the
    kept values are read eight at a time from 256-entry tables of subset sums,
    which makes the standard library fast enough for thousands of flips.
    p never falls below 1 / (reps + 1).
    """
    reps = PERMUTATIONS if reps is None else reps
    n = len(d)
    total = sum(d)
    obs = abs(total)
    if n == 0 or obs == 0:
        return 1.0
    tables = []
    for start in range(0, n, 8):
        chunk = d[start:start + 8]
        t = [0.0] * 256
        for mask in range(1, 256):
            low = mask & -mask
            bit = low.bit_length() - 1
            t[mask] = t[mask ^ low] + (chunk[bit] if bit < len(chunk) else 0.0)
        tables.append(t)
    rng = random.Random(seed)
    tol = 1e-9 * max(1.0, obs)
    hits = 0
    for _ in range(reps):
        bits = rng.getrandbits(8 * len(tables))
        kept = 0.0
        for t in tables:
            kept += t[bits & 255]
            bits >>= 8
        if abs(2 * kept - total) >= obs - tol:
            hits += 1
    return (hits + 1) / (reps + 1)


def hodges_lehmann(d, seed=SEED):
    """Median of the Walsh averages (d_i + d_j) / 2, i <= j.

    Exact up to HL_MAX_PAIRS averages, a seeded random sample of that many
    above, which keeps it fast on large audits.
    """
    n = len(d)
    if n == 0:
        return 0.0
    if n * (n + 1) // 2 <= HL_MAX_PAIRS:
        w = [(d[i] + d[j]) / 2 for i in range(n) for j in range(i, n)]
    else:
        rng = random.Random(seed)
        w = []
        for _ in range(HL_MAX_PAIRS):
            i, j = rng.randrange(n), rng.randrange(n)
            w.append((d[i] + d[j]) / 2)
    w.sort()
    m = len(w)
    return w[m // 2] if m % 2 else (w[m // 2 - 1] + w[m // 2]) / 2


def rank_direction(d):
    """+1 or -1: the side the signed-rank statistic leans to; 0 if balanced.
    Zeros are dropped and ties averaged, exactly as in the test."""
    nz = sorted((x for x in d if x != 0), key=abs)
    n = len(nz)
    total = 0.0
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(nz[j + 1]) == abs(nz[i]):
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            total += r if nz[k] > 0 else -r
        i = j + 1
    return (total > 0) - (total < 0)


def bh(pvals):
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adj = [0.0] * n
    prev = 1.0
    for rank, i in enumerate(reversed(order)):
        k = n - rank
        prev = min(prev, pvals[i] * n / k)
        adj[i] = prev
    return adj


def holm(pvals):
    """Holm step-down: family-wise error, for "does ANY floor move"."""
    n = len(pvals)
    order = sorted(range(n), key=lambda i: pvals[i])
    adj = [0.0] * n
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (n - rank) * pvals[i]))
        adj[i] = running
    return adj


def holm_either(rows):
    """One family-wise error for "does ANY of these move, on EITHER test".

    Holm across every row per test, then Bonferroni across the two tests: the
    reported p_adjusted is min(1, 2 * min(Holm rank, Holm mean)). An earlier
    version corrected each test and each set of rows separately at ALPHA and
    OR-ed the verdicts, which let the false alarm of a quiet floor reach 12
    percent in the tests.
    """
    if not rows:
        return []
    for r, a, b in zip(rows, holm([x["p_rank"] for x in rows]),
                       holm([x["p_mean"] for x in rows])):
        r["p_adjusted_rank"], r["p_adjusted_mean"] = a, b
        r["p_adjusted"] = min(1.0, 2 * min(a, b))
    return [r for r in rows if r["p_adjusted"] < ALPHA]


def claimed(r):
    """An audited interaction counts only if both tests reject after BH and
    the mean and the signed-rank statistic lean the same way."""
    return (r["p_adjusted"] < ALPHA and r["interaction"] != 0
            and r["rank_dir"] != 0
            and (r["interaction"] < 0) == (r["rank_dir"] < 0))


def direction(r):
    if not claimed(r):
        return ""
    ea, eb = r["single_a"], r["single_b"]
    if ea < 0 and eb < 0:
        return ("compounds: costs more than the sum" if r["interaction"] < 0
                else "cost does not add")
    if ea > 0 and eb > 0:
        return ("benefit does not add" if r["interaction"] < 0
                else "benefit compounds")
    return "singles point opposite ways: no direction label"


def test_pair(d):
    lo, hi = boot_ci(d)
    return {"n": len(d), "interaction": mean(d), "ci_low": lo,
            "ci_high": hi, "hl": hodges_lehmann(d),
            "rank_dir": rank_direction(d), "p_rank": signed_rank_p(d),
            "p_mean": sign_flip_p(d), "mde": mde(d)}


def stratified_floors(data, floors):
    """Each floor within thirds of its items, ordered by its own cell mean.

    Returns (rows, skipped floor names).
    """
    rows, skipped = [], []
    for fl in floors:
        own = data[fl["pair"]]["items"]
        key = {item: mean(v) for item, v in own.items()}
        if len(key) < STRATA * MIN_ITEMS:
            skipped.append(fl["pair"])
            continue
        ordered = sorted(key, key=lambda i: (key[i], i))
        size = len(ordered) // STRATA
        for s in range(STRATA):
            part = ordered[s * size:] if s == STRATA - 1 \
                else ordered[s * size:(s + 1) * size]
            d = [interaction(own[i]) for i in part]
            r = test_pair(d)
            r.update({"pair": fl["pair"], "stratum": ("lowest", "middle",
                                                      "highest")[s]
                      if STRATA == 3 else f"stratum {s + 1}"})
            rows.append(r)
    return rows, skipped


def analyse(data):
    rows = []
    for pair, entry in data.items():
        items = list(entry["items"].values())
        d = [interaction(v) for v in items]
        r = test_pair(d)
        r.update({"pair": pair, "kind": entry["kind"],
                  "single_a": mean([v[1] - v[0] for v in items]),
                  "single_b": mean([v[2] - v[0] for v in items])})
        rows.append(r)
    floors = [r for r in rows if r["kind"] == "floor"]
    social = [r for r in rows if r["kind"] == "social"]
    if not floors:
        raise InputError("no floor pairs. Without a floor this test has "
                         "nothing to check the instrument against")
    # Two families, two error rates. The first version corrected everything
    # together with BH, and its own tests caught the result: strong audited
    # effects made the correction more lenient for the floors, so a floor with
    # a true interaction of zero was flagged.
    # One family for the whole floor question: every floor overall and within
    # every stratum, on either test.
    strat_rows, skipped = stratified_floors(data, floors)
    flagged = holm_either(floors + strat_rows)
    moving = [r for r in floors if r in flagged]
    strat_moving = [r for r in strat_rows if r in flagged]
    for r in floors:
        r["correction"] = "holm, either test"
    for r, a in zip(social, bh([max(x["p_rank"], x["p_mean"])
                               for x in social])):
        r["p_adjusted"] = a
        r["correction"] = "bh, both tests"
        r["claimed"] = claimed(r)
        r["direction"] = direction(r)

    warnings = []
    if len(floors) < MIN_FLOORS:
        warnings.append(f"only {len(floors)} floor pair(s); use at least "
                        f"{MIN_FLOORS}, because one neutral pair can itself "
                        f"be unusual")
    for r in rows:
        if r["n"] < MIN_ITEMS:
            warnings.append(f"{r['pair']} has {r['n']} items; below "
                            f"{MIN_ITEMS} the test has little power")
    if skipped:
        warnings.append("stratified floor check not run for "
                        f"{', '.join(skipped)}: it needs at least "
                        f"{STRATA * MIN_ITEMS} items")

    if moving:
        verdict = "CONTAMINATED"
    elif strat_moving:
        verdict = "CLEAN IN AGGREGATE ONLY"
    else:
        verdict = "CLEAN"
    return {"verdict": verdict, "rows": rows, "strata": strat_rows,
            "floors_moving": [r["pair"] for r in moving],
            "floors_moving_within_strata":
                [f"{r['pair']} ({r['stratum']})" for r in strat_moving],
            "warnings": warnings, "n_floors": len(floors),
            "n_social": len(social)}


def print_report(result):
    rows = result["rows"]
    print("=" * 86)
    print("INTERACTION FLOOR TEST")
    print("=" * 86)
    for kind, title in (("floor", "FLOOR PAIRS, should be zero "
                                  "(Holm across the floors, either test)"),
                        ("social", "AUDITED PAIRS "
                                   "(Benjamini-Hochberg, both tests)")):
        sel = [r for r in rows if r["kind"] == kind]
        if not sel:
            continue
        print()
        print(f"  {title}")
        print(f"  {'pair':26}{'n':>5}{'interaction':>12}{'95% CI':>21}"
              f"{'HL':>9}{'MDE':>8}{'p adj':>8}")
        for r in sel:
            if kind == "floor":
                flag = " *" if r["p_adjusted"] < ALPHA else ""
            else:
                flag = " *" if r["claimed"] else ""
            print(f"  {r['pair'][:25]:26}{r['n']:5}{r['interaction']:+12.4f}"
                  f"  [{r['ci_low']:+8.4f},{r['ci_high']:+8.4f}]"
                  f"{r['hl']:+9.4f}{r['mde']:8.4f}{r['p_adjusted']:8.4f}{flag}")
    if result["strata"]:
        print()
        print("  FLOOR PAIRS WITHIN DIFFICULTY THIRDS "
              "(items ordered by their own cell mean; Holm, either test)")
        for r in result["strata"]:
            flag = " *" if r["p_adjusted"] < ALPHA else ""
            print(f"  {r['pair'][:25]:26}{r['stratum']:>9}{r['n']:5}"
                  f"{r['interaction']:+12.4f}{r['p_adjusted']:8.4f}{flag}")
    print()
    print("-" * 86)
    if result["verdict"] == "CONTAMINATED":
        print(f"  VERDICT: FLOOR CONTAMINATED. {len(result['floors_moving'])} "
              f"of {result['n_floors']} neutral pairs interact:")
        print(f"    {', '.join(result['floors_moving'])}")
        print("  This instrument responds to combining text, not to what the")
        print("  text says about a person. None of the audited interactions")
        print("  above can be read as a finding, however significant.")
    elif result["verdict"] == "CLEAN IN AGGREGATE ONLY":
        print("  VERDICT: CLEAN IN AGGREGATE ONLY. The neutral pairs are quiet on")
        print("  average, but move within a difficulty stratum:")
        print(f"    {', '.join(result['floors_moving_within_strata'])}")
        print("  Movements in opposite directions cancel in the average. The")
        print("  instrument still responds to combining text, so none of the")
        print("  audited interactions can be read as a finding.")
    else:
        sig = [r for r in rows if r["kind"] == "social" and r["claimed"]]
        print(f"  VERDICT: FLOOR CLEAN. All {result['n_floors']} neutral pairs "
              f"are quiet, overall and within strata.")
        if sig:
            print("  Audited interactions that survive both tests, with what")
            print("  their sign means given the two single effects:")
            for r in sig:
                print(f"    {r['pair']:28}{r['interaction']:+.4f}  "
                      f"singles {r['single_a']:+.3f} {r['single_b']:+.3f}  "
                      f"{r['direction']}")
        else:
            print("  No audited interaction survives both tests. Read the MDE")
            print("  column before calling that absence: it is the smallest")
            print("  interaction this data could have seen.")
    for w in result["warnings"]:
        print(f"  WARNING: {w}")
    print("-" * 86)


def main(argv):
    args = list(argv)
    json_out = None
    if "--json" in args:
        i = args.index("--json")
        if i + 1 >= len(args):
            print("--json needs a file name", file=sys.stderr)
            return 1
        json_out = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print("usage: floor_test.py results.csv [--json report.json]",
              file=sys.stderr)
        return 1
    try:
        result = analyse(read(args[0]))
    except InputError as e:
        print(f"input not usable: {e}", file=sys.stderr)
        return 1
    print_report(result)
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    return 0 if result["verdict"] == "CLEAN" else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
