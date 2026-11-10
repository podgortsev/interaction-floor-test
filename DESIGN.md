# Designing an interaction audit that can be checked

Every rule below was learned by getting it wrong first, in Paper 2 or Paper 3 of
the Average-Fit programme. Each one changed a conclusion.

---

## Building the four versions

**1. Hold the number of statements constant, not only the length.**
Every version of a case says the same number of things. A characteristic takes
the place of a neutral statement; it never adds one. Otherwise "two
characteristics" also means "one more sentence", and the audit measures
verbosity.

**2. Match length by whole statements.** Pad to a target with complete neutral
sentences, never by cutting or stretching one mid-phrase. A 40-word preamble
changed one model's accuracy by ten points on its own.

**3. Put each characteristic in the same position in the single and the combined
version.** If "uses a screen reader" is the first statement in the combined
case, it is the first statement in the single case it is compared with.
Otherwise position differences leak into the interaction.

**4. Run both orders wherever order can vary.** Two stated characteristics can
appear in either order; run both. A result that holds in one order only belongs
to the position, not the person.

## Building the floor

**5. Build at least three floor pairs.** A floor pair is two socially neutral but
distinctive details, built exactly like the audited pairs. One pair is not
enough: a single neutral statement can turn out not to be neutral at all.

**6. Neutral means no cue about age, disability, health, language, nationality,
religion, family, gender, class or education.** Check the words, not only the
meaning. "Reads crime novels" is a harmless hobby and still contains the word
"crime", and an instrument that reads text reads words.

**7. Distinctive means real information.** "I cycle to work" is a fact about a
person. Filler such as "I have a question" is not a floor, it is padding.

## Measuring

**8. Keep outcomes paired within the item.** Every version of a case faces the
same task, profile or question. Compare within the item. Comparing averages
across items hid effects that the paired test found.

**9. Never build an interaction by differencing margins measured against a shared
reference.** If a two-option choice compares A against a neutral version, and
separately the combined version against the same neutral version, subtracting
the two is not an interaction: the combined version differs from the reference
in two places and each single in one. Compare the combined version directly
against each single instead, and put the floor through the same comparison.

**10. Check the instrument is producing what you think it reads.** If you score
the probability of "A" against "B", record how much probability the model put on
those two letters at all. Where most of it is elsewhere, the model was not about
to choose, and the read is not a judgement.

**11. Collect the reference twice if the study runs in more than one session.**
Two copies of the neutral version, collected separately, should agree. If they
do not, results depend on the session, and nothing compared across sessions can
be trusted.

## Reading

**12. Read the floor first.** Before any audited result. One significant floor
pair contaminates the instrument; the audit does not get to choose the floor it
prefers.

**13. Correct the floors and the audited pairs as two separate families.** The
floors answer "does ANY neutral pair move", so they need family-wise control
(Holm) among themselves. The audited pairs are a search for discoveries, so they
need false-discovery control (Benjamini-Hochberg) among themselves. Correcting
both together looks thorough and is wrong: strong audited effects make the
correction more lenient for the floors, so the more an audit finds, the easier a
quiet floor is flagged.

**14. Report the minimum detectable effect next to every null.** An interaction
is a difference of differences and carries about twice the variance of a single
difference. A null without that number reads as "no effect" when it may only
mean "not visible from here".

**15. Register what counts as confirmation and as refutation before collecting.**
With hundreds of numbers, some combination always supports something.

**16. Test a continuous outcome twice, and let the rule only remove claims.** A
mean and a signed-rank test answer different questions. With many items at a
ceiling and a few large moves elsewhere, a floor had a mean of +0.18 with an
interval excluding zero and a signed-rank p of 0.87. Picking the test after
seeing that is a forking path. A floor moves if either test rejects; an audited
effect counts only if both do.

**17. Check the floor within difficulty strata, and treat the whole floor
question as one family.** A neutral pair can move up on hard items and down on
easy ones and sum to nothing. Order items by a difficulty measure that weighs the
four cells equally, such as their mean, which the interaction's +1, -1, -1, +1
cancels. Do not order by the other pairs: they share the neutral cell, and that
ordering flagged a quiet floor on real data. Then correct every floor test,
overall and within strata, on both tests, as one family; correcting each view
separately let a quiet floor be flagged 12 percent of the time.

**18. Read the sign of an interaction against the signs of its singles.** "More
negative than the sum" is compounding harm only if each single is a cost. When
each single helps, it means the help does not add. In Paper 3 every interaction
a probability instrument registered, neutral or social, was a second statement
adding less than the first.
