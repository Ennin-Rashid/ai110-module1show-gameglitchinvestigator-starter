# 💭 Reflection: Game Glitch Investigator

> **Note to self:** the Bug Reproduction Log below is factual and verified. The
> written answers are a first draft based on what actually happened during the
> session — rewrite them in your own voice before submitting, and cut anything
> that does not match your own experience.

## 1. What was broken when you started?

The first run looked convincing — a titled page, a difficulty selector, a
debug expander showing the secret — which is exactly what made it hard to
trust. The first guess already went wrong: the app labelled a guess "Too High"
and in the same breath told me to "Go HIGHER!". By the second guess the hints
stopped agreeing with themselves entirely, because the secret was being cast
to a string on even-numbered attempts and compared lexicographically, so a
guess of 9 against a secret of 50 came back as "too high". The two bugs I
could name immediately were **the hints were backwards** and **"New Game" did
nothing once you had won or lost** — the status flag was never reset, so the
`st.stop()` guard trapped the app on the game-over screen until I restarted
the server. Underneath those, the score was moving in whichever direction the
attempt counter's parity felt like. Worth naming the categories: there were
**no syntax errors at all** — the file parsed and the app booted on the first
try, which is exactly what made it feel trustworthy. What it had was one
**runtime** bug (a `TypeError` from comparing `int > str`) and eight **logic**
bugs. The runtime error was the only one Python itself objected to, and a bare
`except TypeError` caught it and turned it into a wrong answer, so even that
one never surfaced. AI-generated code tends to fail this way: the syntax is
free, and every bug lives in the meaning.

**Bug Reproduction Log**

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
|-------|-------------------|-----------------|------------------------|
| Secret 50, guess `60` (attempt 1) | Hint says go LOWER | Labelled "Too High" but message read `📈 Go HIGHER!` | No error — silently wrong |
| Secret 50, guess `9` (attempt 2) | "Too Low" | `('Too High', '📈 Go HIGHER!')` — secret was `str`, so `"9" > "50"` compared as text | `TypeError` raised then swallowed by `except TypeError` in `check_guess` |
| Secret 50, guess `100` (attempt 2) | "Too High" | `('Too Low', '📉 Go LOWER!')` — `"100" < "50"` as text | Same swallowed `TypeError` |
| Win on the first guess | Score 100 | Score 70 (`attempts` started at 1 and was incremented before scoring) | No error |
| Guess `60` (too high) on attempt 2 | Score goes down | Score went **up** by 5 — `update_score` added points when `attempt_number % 2 == 0` | No error |
| Type `abc`, press Submit | Error message, attempt not counted | Error shown **and** an attempt consumed; no loss check on that branch | No error |
| Guess `5.9` on a 1–100 board | Rejected as not a whole number | Silently truncated to `5` | No error |
| Press "New Game" after losing | Fresh round | Game-over screen again, permanently — `status` never reset | No error |
| `python -m pytest tests/` | Tests run | 3 failed | `NotImplementedError: Refactor this function from app.py into logic_utils.py` |

## 2. How did you use AI as a teammate?

I used Claude (in Claude Code) as the main assistant on this one. The useful
move was refusing to let it — or me — fix anything by reading alone. Before
touching the code I had it write a throwaway script that loaded only the pure
functions out of `app.py` (skipping the Streamlit UI) and called them with
known inputs, so every bug was printed as real output first. That is how the
string-comparison bug became undeniable: `check_guess(9, "50")` printing
`Too High` is not something you can argue with, whereas "I think this except
block might be wrong" is.

**A suggestion I accepted:** the fix for the starter tests expecting
`check_guess` to return a bare string while `app.py` returned a tuple — split
the comparison from the wording, so `check_guess` returns only the outcome and
a separate `hint_for()` maps the outcome to the player-facing message. I
verified it by running the three unmodified starter tests, which then passed
without editing them. Treating the given tests as the spec rather than as
something to bend was the right instinct.

**A suggestion I changed:** the first pass at `parse_guess` kept the original
`int(float(raw))` behaviour for inputs like `"5.9"`. It works, but it silently
decides what the player meant, which is the same class of mistake as the rest
of this codebase — quietly doing something plausible instead of saying what
happened. I changed it to reject decimals with their own message. I also
pushed back on clamping the score at zero at first, then kept it, because a
negative score in a casual guessing game is noise rather than information.
Both changes are pinned by tests, which is how I know the behaviour is what I
think it is.

**A suggestion I rejected outright:** the starter README told me the secret
number "changes every time you click Submit" and pointed me at the prompt
*"How do I keep a variable from resetting in Streamlit when I click a button?"*
I checked before asking it, and the claim was false — the secret was already
correctly guarded behind `if "secret" not in st.session_state`, so it was never
being regenerated. Asking that question would have produced a confident,
well-formatted answer about `st.session_state` for a bug that does not exist:
a **hallucination** invited by a bad premise rather than by the model. The
symptom was real, but the cause was the opposite one — state that persisted
when it should have been cleared, because "New Game" never reset `status`. So
I dropped the suggested prompt and sat with the debug expander open until I
could see which value was actually wrong. That is the **human-in-the-loop**
part of this workflow doing real work: an AI can only answer the question you
ask it, and deciding *which question is worth asking* stayed my job.

## 3. Debugging and testing your fixes

A bug counted as fixed when a test that failed against the old code passed
against the new code — not when the app "looked right". The test I care most
about is
`test_binary_search_always_wins_within_the_attempt_limit`: it plays a perfect
binary search against **every** possible secret at **every** difficulty and
fails if any one of them is unwinnable within the attempt limit. That single
test is the one that would have caught the original "you can't win" complaint
without anyone having to play the game, and it is also what caught that Hard
mode had been given the fewest attempts. Running it forced a real design
decision: Hard had to become 1–200 with 10 attempts, because 1–50 with 5
attempts is not solvable in the worst case. The suite went from 3 failing to
49 passing.

Two habits carried the weight here. First, a bug was never "fixed" on the
strength of reading the patch — **verification** meant a test that failed
before the change and passed after it, plus a run of the real app in a browser
to confirm the fix survived contact with Streamlit's rerun model. That second
step earned its keep: it caught a bug in *my own* rewrite, where the score and
attempts-left metrics render above the submit handler and so displayed the
state from before the guess. Every unit test was green while the UI was
visibly lying. Second, the **test set** is deliberately wider than the three
starter cases — it pins the boundaries (1, and the top of each range), the
invalid inputs, the scoring curve, and the exact wrong answers the old code
used to give, so every bug in the log above now has a test that fails if it
ever comes back.

AI helped most with the boring half of testing — generating the parametrised
edge cases for `parse_guess` (empty, whitespace, `None`, `"50abc"`, negatives,
out-of-range) faster than I would have listed them. I still had to decide what
the *correct* answer for each case was; it was good at enumerating inputs and
not authoritative about expected behaviour.

## 4. What did you learn about Streamlit and state?

Streamlit re-runs the entire script from the top every time you touch a widget
— there is no event handler, the whole file just executes again. So every
normal Python variable is rebuilt from scratch on every click, and the only
thing that survives is what you put in `st.session_state`.

The twist here is that the starter code got the famous half of this right. The
secret *was* guarded with `if "secret" not in st.session_state`, so it was not
actually being regenerated. The bug was the mirror image: state that persisted
when it should have been cleared. `status` stayed `"lost"` across every rerun
because "New Game" reset `attempts` and `secret` but forgot it, and the
`st.stop()` guard turned that one stale value into a permanent dead end. So
the rule I would give a friend has two halves: anything that must outlive a
click goes in `session_state`, **and** every piece of state in there needs
exactly one function that knows how to reset all of it together. Scattering
four separate assignments across a button handler is how you end up forgetting
the fifth.

## 5. Looking ahead: your developer habits

The habit I want to keep is **reproduce before you repair**. Writing the
throwaway script that printed each wrong output before I changed a line meant
I fixed the bugs that existed rather than the bugs I assumed existed — and it
gave me the exact assertions for the regression tests for free. The second
habit is treating an existing test file as a specification: the starter tests
told me what `check_guess` was supposed to return, and the design fell out of
honouring that instead of rewriting the tests to match my code.

Next time I would ask the AI for the failing test *before* asking it for the
fix. On a couple of these bugs I let it propose a patch first, and a patch
always looks reasonable — the test is what tells you whether it is.

What this changed about how I read AI-generated code: the code was never
badly formed. It had docstrings, type hints, sensible function names and a
debug panel. Every bug lived in the gap between what a name promised and what
the body did — a function called `check_guess` returning a hint pointing the
wrong way, an `update_score` that sometimes awarded points for being wrong, a
bare `except TypeError` that turned a crash into a confident lie. Fluent code
is not evidence of correct code, and the bugs that survive review are the ones
that never raise anything.
