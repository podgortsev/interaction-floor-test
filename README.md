# Interaction Floor Test

**Does your bias audit measure people, or words?**

Private product. Not part of any paper repository, not published.

---

## The question it answers

Many AI fairness audits ask whether two characteristics together hurt a person
more than each one does alone: a screen reader user who is also 74, a non-native
speaker who also makes typos. The test is an interaction, measured on four
versions of the same case: neither characteristic, the first, the second, both.

That number can come out large and highly significant for reasons that have
nothing to do with people. Instruments that read a language model's
probabilities can respond to the combination of any two pieces of text,
including two that mean nothing socially. Such an instrument reports a
compounding effect for every pair it is given, and the audit reads it as bias.

This tool checks for exactly that, before anyone reports a result.

## Where it comes from

Paper 3 of the Average-Fit research programme, Stacked Human-AI Fit, audited
three open language models with five instruments. Alongside the pairs of
disclosures it stacked pairs of socially neutral details, built exactly the same
way: cycling to work, baking bread, walking a dog.

Two of the three instruments that read model probabilities reported large and
significant interactions between those neutral details. The mechanism was
visible in the data: the effect of a clause depended on the clause next to it,
so the same harmless detail helped or hurt depending on its neighbour. A fourth
instrument, the probability of the correct answer, looked clean on one model
until the floors were checked within difficulty strata. The only instrument
whose neutral pairs stayed at zero everywhere was whether the model solved the
person's own task.

A published audit without that check could not have told the two apart.

## Use

    python floor_test.py results.csv
    python floor_test.py results.csv --json report.json

| exit code | meaning |
|---|---|
| 0 | floor clean: the audited interactions can be read |
| 2 | floor contaminated, overall or within a difficulty stratum: this instrument cannot identify an interaction |
| 1 | the input could not be used |

Python 3.8 or later, standard library only.

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
pair can itself be unusual.

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
The audited interactions can be read, with the minimum
detectable effect beside each one: an absence of evidence smaller than that
number is not evidence of absence.

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

## Building the floor

The test is only as good as the floor pairs, and the floor pairs are only as
good as the design. `CHECKLIST.md` lists every rule, each one learned by getting
it wrong first.

## Files

    floor_test.py        the tool
    test_floor_test.py   proves the verdicts on data with a known answer
    make_examples.py     writes examples/clean.csv and examples/contaminated.csv
    CHECKLIST.md         how to design an audit this test can check
    doc/                 the same, as a four-page PDF

## Status

Private. Licence not chosen. Working prototype, tested on synthetic data with
known answers (55 checks, including false-alarm rates over many seeds). Run on
Paper 3's real outputs for task accuracy and answer probability on three models,
it reaches the same six verdicts as the paper's own analysis, which stratifies
differently.
