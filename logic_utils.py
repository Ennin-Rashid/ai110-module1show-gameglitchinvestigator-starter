"""Pure game logic for the Number Guessing Game.

Everything in this module is free of Streamlit imports and global state so it
can be unit tested directly. `app.py` owns the UI and session state; this
module owns the rules.
"""

# FIX: Hard was 1-50 (narrower than Normal's 1-100) while also giving the
# fewest attempts. Claude flagged it when a test asserted the ranges should
# widen with difficulty; I picked the new numbers and checked each is still
# winnable by binary search within its attempt limit.
DIFFICULTY_RANGES = {
    "Easy": (1, 20),
    "Normal": (1, 100),
    "Hard": (1, 200),
}

DIFFICULTY_ATTEMPTS = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 10,
}

DEFAULT_DIFFICULTY = "Normal"

WIN = "Win"
TOO_HIGH = "Too High"
TOO_LOW = "Too Low"

HINTS = {
    WIN: "🎉 Correct!",
    TOO_HIGH: "📉 Too high — go LOWER!",
    TOO_LOW: "📈 Too low — go HIGHER!",
}

MAX_WIN_POINTS = 100
POINTS_LOST_PER_ATTEMPT = 10
MIN_WIN_POINTS = 10
WRONG_GUESS_PENALTY = 5


def get_range_for_difficulty(difficulty: str):
    """Return the inclusive (low, high) range for a difficulty.

    Unknown difficulties fall back to Normal.
    """
    return DIFFICULTY_RANGES.get(difficulty, DIFFICULTY_RANGES[DEFAULT_DIFFICULTY])


def get_attempt_limit(difficulty: str) -> int:
    """Return how many guesses a player gets at this difficulty."""
    return DIFFICULTY_ATTEMPTS.get(difficulty, DIFFICULTY_ATTEMPTS[DEFAULT_DIFFICULTY])


# FIX: Claude's first pass kept the original int(float(raw)) so "5.9" became 5.
# I rejected that — silently deciding what the player meant is the same class of
# mistake as the rest of this codebase — and had it reject decimals instead.
# Range validation is new: out-of-range guesses used to be accepted.
def parse_guess(raw, low=None, high=None):
    """Parse raw text input into an integer guess.

    Returns ``(ok, guess_int, error_message)``. Exactly one of ``guess_int``
    and ``error_message`` is ever non-None.

    Rejects (rather than silently truncating) decimals such as "5.9", and
    rejects guesses outside ``[low, high]`` when a range is supplied.
    """
    if raw is None:
        return False, None, "Enter a guess."

    text = str(raw).strip()
    if not text:
        return False, None, "Enter a guess."

    try:
        value = int(text)
    except ValueError:
        # Give a decimal its own message so the player knows why it bounced.
        try:
            float(text)
        except ValueError:
            return False, None, f"'{text}' is not a number."
        return False, None, "Whole numbers only — no decimals."

    if low is not None and high is not None and not (low <= value <= high):
        return False, None, f"Guess must be between {low} and {high}."

    return True, value, None


# FIX: two bugs here. The hints were inverted ("Too High" told you to go
# HIGHER), and app.py stringified the secret on even attempts, so a bare
# `except TypeError` re-compared both values as text ("9" > "50") and produced
# confident lies. Refactored out of app.py into this module with Claude in
# agent mode; the int() coercion and the deleted except clause are the fix.
# Returning a bare outcome string (not a tuple) is what the starter tests
# already specified — I kept their contract instead of rewriting them.
def check_guess(guess, secret) -> str:
    """Compare a guess to the secret and return the outcome.

    Returns one of ``"Win"``, ``"Too High"`` or ``"Too Low"``.

    Both arguments are coerced to ``int`` first. That coercion is deliberate:
    the original app stored the secret as a string on alternating turns, which
    made Python compare the two values lexicographically ("9" > "50") and
    produced hints that were confidently wrong.
    """
    guess = int(guess)
    secret = int(secret)

    if guess == secret:
        return WIN
    if guess > secret:
        return TOO_HIGH
    return TOO_LOW


def hint_for(outcome: str) -> str:
    """Return the player-facing message for an outcome."""
    return HINTS.get(outcome, "")


# FIX: a first-guess win paid 70 because attempts started at 1 and was
# incremented before scoring, and "Too High" *awarded* +5 on even attempts
# (`if attempt_number % 2 == 0`) while "Too Low" always subtracted. Claude
# spotted the parity branch; I chose the 1-based attempt_number contract and
# the clamp at zero, both pinned by tests.
def update_score(current_score: int, outcome: str, attempt_number: int) -> int:
    """Return the new score after an attempt.

    ``attempt_number`` is 1-based: the number of the guess just played. A win
    on the first guess is worth the full ``MAX_WIN_POINTS``, and every extra
    attempt costs ``POINTS_LOST_PER_ATTEMPT``, never dropping below
    ``MIN_WIN_POINTS``. A wrong guess costs ``WRONG_GUESS_PENALTY``, and the
    score is clamped at zero so it can never go negative.
    """
    if outcome == WIN:
        points = MAX_WIN_POINTS - POINTS_LOST_PER_ATTEMPT * (attempt_number - 1)
        points = max(points, MIN_WIN_POINTS)
        return current_score + points

    if outcome in (TOO_HIGH, TOO_LOW):
        return max(0, current_score - WRONG_GUESS_PENALTY)

    return current_score
