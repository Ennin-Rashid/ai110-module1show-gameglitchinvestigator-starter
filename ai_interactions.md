# AI Interactions Log

> **Stretch features only.** Only the sections for stretch features actually
> attempted are filled in. This project attempted **Challenge 1: Advanced
> Edge-Case Testing**, so section SF7 is complete and the rest are left blank.

---

## Test Generation (SF7)

> How AI was used to find and cover edge cases that survived the main repair.

### Prompts used

**Prompt 1 — find the cases, don't assume them**

```
The main repair already rejects decimals, non-numbers and out-of-range
guesses. Don't re-test those. Find three classes of input that would STILL
break parse_guess, and attack Python's own numeric parsing rather than the
obvious user typos. Write a probe script that calls parse_guess directly and
prints the actual return value for each candidate, so I can see what breaks
before anything is changed.
```

This phrasing mattered. Asking "what edge cases should I test?" produces a
generic list (negatives, zero, very large numbers) that the existing suite
already covered. Asking what could break *Python's parsing* is what surfaced
PEP 515 underscores and the 4300-digit `int(str)` limit.

**Prompt 2 — confirm the mechanism before fixing**

```
For each failing case, show me the underlying Python behaviour that causes it
(the exact exception or return value), not just the symptom.
```

**Prompt 3 — generate the tests**

```
Write pytest cases for these three classes. Parametrise them, and in each
test's comment record what the old behaviour was so the test explains why it
exists. Add one test asserting that no input is ever rejected with an empty
message and that nothing is blamed on decimals unless the input actually
contains a "." character.
```

### Edge cases and results

| Edge Case | Prompt Used | AI-Suggested Test | Did It Pass? | Your Reasoning |
|-----------|-------------|-------------------|--------------|----------------|
| `"9" * 5000` (5000-digit integer) | Prompts 1–3 | `test_absurdly_long_number_is_rejected_as_too_large` | Failed first, passes now | Chosen because "extremely large values" usually means *numerically* large, but the real cliff is textual: CPython raises `ValueError` on `int(str)` past 4300 digits. The old fallback then called `float()`, which returns `inf` rather than raising, so a huge integer was reported as *"Whole numbers only — no decimals."* |
| `"inf"`, `"-inf"`, `"nan"`, `"Infinity"` | Prompts 1–3 | `test_float_keywords_are_not_numbers` | Failed first, passes now | Chosen because `float()` accepts these words while `int()` does not, so they slipped into the decimal branch. An input containing no digits at all was being blamed on a decimal point. |
| `"1_0"`, `"٤٢"`, `"１０"`, `"1e3"` | Prompts 1–3 | `test_non_plain_digit_spellings_are_rejected_not_reinterpreted` | Failed first, passes now | The serious one. `int()` honours PEP 515 underscore separators and *any* Unicode decimal digit, so `"1_0"` became 10 and `"٤٢"` became 42 — **silently accepted**, and an attempt was charged for a number the player never typed. Same class of bug as the original `int(float("5.9"))` truncation. |
| `" 50"`, `"50\n"`, `"\t50 "` | Prompt 3 | `test_surrounding_whitespace_is_forgiven` | Passed first time | A guard, not a bug. Tightening the parser risked rejecting pasted text with a non-breaking space. Python's `str.strip()` treats `\xa0` as whitespace, so this must keep working — the test pins that it does. |
| Every rejected input | Prompt 3 | `test_every_rejection_explains_itself` | Passed after the fix | A property test rather than a case test: no input may be rejected with an empty message, and nothing may be blamed on decimals unless it contains a `.`. This is what actually encodes the lesson, since all three bugs above were *misleading messages or silent acceptance*, not crashes. |

### What I changed about the AI's output

The first suggested fix special-cased each bad input with its own `if`. I
rejected that — it only handles the inputs you happen to think of. Validating
the *shape* of the input first (`re.compile(r"[+-]?[0-9]+\Z")`) and treating
everything else as suspect is closed by default, so the next exotic numeric
spelling is rejected without a code change.

### Verification

`pytest` output is in [`test_results.txt`](test_results.txt) and pasted into
the README: **64 passed**, up from 49.

One verification step is worth recording because it nearly produced a false
conclusion. After the fix, the live app *still* accepted `1_0` as 10 and
charged an attempt, while the unit test said it was rejected. The code was
correct: Streamlit reran `app.py` on save but kept the already-imported
`logic_utils` module in memory, so the browser was exercising the old parser.
Restarting the server on a clean port showed the correct message and the
attempt counter staying put. Had I trusted the browser over the test, I would
have "fixed" a bug that did not exist.

---

## Agent Workflow (SF8)

*Not attempted.*

---

## Linting & Style (SF9)

*Not attempted.*

---

## Model Comparison (SF11)

*Not attempted.*
