# Interaction Floor Test

**Does your bias audit measure people, or words?**

An audit that finds two characteristics compounding may be reporting nothing
more than its instrument responding to two pieces of text, because many
instruments that read a language model's probabilities interact for any two
details, including two that mean nothing socially. This tool takes the audit's
four-cell outcomes together with pairs of socially neutral details stacked the
same way, and reports whether the neutral pairs interact too, which decides
whether any audited interaction can be read at all.

## Run it

From a clone of this folder, with Python 3.8 or later and nothing installed:

    python floor_test.py examples/clean.csv

Output, copied from that run:

    ======================================================================================
    INTERACTION FLOOR TEST
    ======================================================================================

      FLOOR PAIRS, should be zero (Holm across the floors, either test)
      pair                          n interaction               95% CI       HL     MDE   p adj
      cycling_x_bread             150     -0.0361  [ -0.1352, +0.0604]  -0.0401  0.0976  1.0000
      dog_x_guitar                150     +0.0971  [ +0.0013, +0.1893]  +0.0917  0.0970  1.0000
      tea_x_books                 150     +0.0712  [ -0.0212, +0.1690]  +0.0644  0.0983  1.0000

      AUDITED PAIRS (Benjamini-Hochberg, both tests)
      pair                          n interaction               95% CI       HL     MDE   p adj
      screen_reader_x_age         150     -0.3825  [ -0.4770, -0.2845]  -0.3807  0.0970  0.0002 *
      adhd_x_deaf                 150     -0.0148  [ -0.1125, +0.0866]  -0.0099  0.1024  0.8336

      FLOOR PAIRS WITHIN DIFFICULTY THIRDS (items ordered by their own cell mean; Holm, either test)
      cycling_x_bread              lowest   50     -0.0567  1.0000
      cycling_x_bread              middle   50     -0.0429  1.0000
      cycling_x_bread             highest   50     -0.0087  1.0000
      dog_x_guitar                 lowest   50     -0.0244  1.0000
      dog_x_guitar                 middle   50     +0.1070  1.0000
      dog_x_guitar                highest   50     +0.2088  0.4608
      tea_x_books                  lowest   50     -0.0565  1.0000
      tea_x_books                  middle   50     +0.2027  0.4608
      tea_x_books                 highest   50     +0.0673  1.0000

    --------------------------------------------------------------------------------------
      VERDICT: FLOOR CLEAN. All 3 neutral pairs are quiet, overall and within strata.
      Audited interactions that survive both tests, with what
      their sign means given the two single effects:
        screen_reader_x_age         -0.3825  singles -0.361 -0.316  compounds: costs more than the sum
    --------------------------------------------------------------------------------------

The second example, `examples/contaminated.csv`, differs in one neutral pair
and ends in `VERDICT: FLOOR CONTAMINATED` with exit code 2. Both expected
reports are in `examples/`, to the last digit, and the tests check them.

| exit code | meaning |
|---|---|
| 0 | floor clean: the audited interactions can be read |
| 2 | floor contaminated, overall or within a difficulty stratum: this instrument cannot identify an interaction |
| 1 | the input could not be used |

    python floor_test.py results.csv --json report.json

writes the same report as JSON. The tool reads one file and writes at most one.
It makes no network connection, needs no key, and uses no package outside the
standard library.

## Input

One row per pair and item:

    pair,kind,item,none,a,b,both

| column | meaning |
|---|---|
| `pair` | a name for the pair |
| `kind` | `social` for a pair being audited, `floor` for a neutral pair |
| `item` | the unit the four versions share: a task, a profile, a question. Use the same name in every pair that uses the same unit |
| `none`, `a`, `b`, `both` | the outcome in each version, on one scale: 0 or 1, a score, a log probability |

Use at least three floor pairs. The tool warns below that, because one neutral
pair can itself be unusual. A missing column, an unknown kind, a duplicated
item, an empty, non-numeric, NaN or infinite cell, or a file with no floor pair
stops the run with exit code 1 and a message naming the line. Nothing is
guessed.

## Reading the verdict

Every pair is tested twice: by signed rank, and by a sign-flip permutation test
on the mean, which is the number reported. On outcomes with a ceiling and a
heavy tail the two disagree, and choosing between them after seeing the data is
a forking path. So the rule only ever takes claims away: a neutral pair moves if
EITHER test rejects, and an audited pair counts only if BOTH do.

**CLEAN** means every neutral pair is quiet, overall and within thirds of the
items ordered by difficulty, under one family-wise correction for the whole
question: Holm across every floor test, then Bonferroni across the two tests.
Audited pairs are corrected separately, among themselves (Benjamini-Hochberg).
The audited interactions can be read, with the minimum detectable effect beside
each one: an absence of evidence smaller than that number is not evidence of
absence.

**CONTAMINATED** means at least one neutral pair interacts. One is enough. The
instrument responds to combining text, and no audited interaction it reports can
be treated as a finding, however significant. Nothing in the arithmetic repairs
this; the fix is a different instrument.

**CLEAN IN AGGREGATE ONLY** means the neutral pairs are quiet on average but at
least one moves within a difficulty stratum, typically one way on easy items and
the other way on hard ones. The average hides it; the instrument is contaminated
all the same. Items are ordered by the mean of the pair's own four cells, which
the interaction weighs +1, -1, -1, +1, so the ordering does not bias it.
Ordering by the other pairs looks cleaner and is not: pairs from one run share
the same neutral cell, and the first version of this check flagged a quiet floor
on real data for exactly that reason.

**What a sign means.** A negative interaction is compounding harm only when both
single characteristics are costs. When both help, a negative interaction is a
benefit that does not add. The report labels every audited interaction by the
direction of its two single effects.

## Where it comes from

Paper 3 of the Average-Fit research programme, *Bread and Bicycles*
(DOI 10.5281/zenodo.23959679), audited three open language models with five
instruments. Alongside the pairs of disclosures it stacked pairs of socially
neutral details, built exactly the same way: cycling to work, baking bread,
walking a dog.

Two of the three instruments that read model probabilities reported large and
significant interactions between those neutral details on every model. The
mechanism was visible in the data: the effect of a clause depended on the clause
next to it, so the same harmless detail helped or hurt depending on its
neighbour. A fourth instrument, the probability of the correct answer, looked
clean on one model until the floors were checked within difficulty strata. The
only instrument whose neutral pairs stayed at zero everywhere was whether the
model solved the person's own task.

A published audit without that check could not have told the two apart. On the
paper's own data this tool reaches the same verdicts as the paper's analysis,
through a different stratification.

## Building the floor

The test is only as good as the floor pairs, and the floor pairs are only as
good as the design. `DESIGN.md` lists every rule, each one learned by getting it
wrong first. `doc/interaction-floor-test.pdf` is the same material as a
four-page manual.

## Limits

It does not repair a contaminated instrument. It does not accept margins that
were each measured against a shared reference, because differencing those is
not an interaction. It does not tell you whether your floor pairs are really
neutral, which is a judgement about words and stays with the author. And a
clean floor is not a guarantee of a good audit: it removes one specific way of
being wrong.

## Tests

    python tests/test_floor_test.py

63 checks, about a minute: verdicts on data with known answers, false-alarm
rates measured over many seeds rather than one, a correction flaw that these
tests once caught, a ceiling-and-heavy-tail world where the two tests disagree,
floors that cancel across strata, binary outcomes where most differences are
exactly zero, a biased stratifier an earlier version used, every refused input,
and the two shipped examples reproduced to the last digit.

## Files

    floor_test.py              the tool
    tests/test_floor_test.py   the checks
    test_floor_test.py         runs the same checks from the root
    make_examples.py           regenerates examples/clean.csv and examples/contaminated.csv
    examples/                  the two inputs and their expected reports
    DESIGN.md                  how to design an audit this test can check
    doc/                       the same, as a four-page PDF
    CHECKLIST.md               the release bar, ticked
    LICENSE                    MIT
