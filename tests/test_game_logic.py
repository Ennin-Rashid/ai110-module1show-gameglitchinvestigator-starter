import pytest

from logic_utils import (
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    hint_for,
    parse_guess,
    update_score,
)


# --- Original starter tests (unchanged) -------------------------------------

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    result = check_guess(50, 50)
    assert result == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    result = check_guess(60, 50)
    assert result == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    result = check_guess(40, 50)
    assert result == "Too Low"


# --- Regression: hints used to point the wrong way --------------------------

def test_hint_tells_player_to_go_lower_when_too_high():
    assert "LOWER" in hint_for(check_guess(60, 50))

def test_hint_tells_player_to_go_higher_when_too_low():
    assert "HIGHER" in hint_for(check_guess(40, 50))


# --- Regression: secret was stringified on alternating turns ----------------
# "9" > "50" lexicographically, so a string secret produced confident lies.

@pytest.mark.parametrize("guess, secret, expected", [
    (9, "50", "Too Low"),
    (60, "50", "Too High"),
    (100, "50", "Too High"),
    ("50", 50, "Win"),
])
def test_numeric_strings_compare_numerically_not_lexicographically(guess, secret, expected):
    assert check_guess(guess, secret) == expected


# --- Boundaries -------------------------------------------------------------

@pytest.mark.parametrize("guess, secret, expected", [
    (1, 1, "Win"),
    (2, 1, "Too High"),
    (99, 100, "Too Low"),
    (100, 100, "Win"),
])
def test_check_guess_at_range_edges(guess, secret, expected):
    assert check_guess(guess, secret) == expected


# --- parse_guess ------------------------------------------------------------

def test_parse_guess_accepts_plain_integer():
    assert parse_guess("42", 1, 100) == (True, 42, None)

def test_parse_guess_strips_surrounding_whitespace():
    assert parse_guess("  42  ", 1, 100) == (True, 42, None)

@pytest.mark.parametrize("raw", ["", "   ", None])
def test_parse_guess_rejects_empty_input(raw):
    ok, value, error = parse_guess(raw, 1, 100)
    assert (ok, value) == (False, None)
    assert error == "Enter a guess."

@pytest.mark.parametrize("raw", ["abc", "50abc", "!!"])
def test_parse_guess_rejects_non_numbers(raw):
    ok, value, error = parse_guess(raw, 1, 100)
    assert (ok, value) == (False, None)
    assert "not a number" in error

def test_parse_guess_rejects_decimals_instead_of_truncating():
    # The buggy version turned "5.9" into 5 without telling the player.
    ok, value, error = parse_guess("5.9", 1, 100)
    assert (ok, value) == (False, None)
    assert "Whole numbers" in error

@pytest.mark.parametrize("raw", ["0", "101", "-7", "99999"])
def test_parse_guess_rejects_out_of_range(raw):
    ok, value, error = parse_guess(raw, 1, 100)
    assert (ok, value) == (False, None)
    assert "between 1 and 100" in error

def test_parse_guess_allows_any_value_when_no_range_given():
    assert parse_guess("99999") == (True, 99999, None)


# --- Scoring ----------------------------------------------------------------

def test_first_guess_win_scores_full_points():
    # The buggy version paid 70 for a perfect first guess.
    assert update_score(0, "Win", 1) == 100

@pytest.mark.parametrize("attempt, expected", [(1, 100), (2, 90), (3, 80), (5, 60)])
def test_win_points_decay_by_ten_per_attempt(attempt, expected):
    assert update_score(0, "Win", attempt) == expected

def test_win_points_never_fall_below_the_floor():
    assert update_score(0, "Win", 50) == 10

@pytest.mark.parametrize("outcome", ["Too High", "Too Low"])
@pytest.mark.parametrize("attempt", [1, 2, 3, 4])
def test_wrong_guesses_always_cost_the_same_regardless_of_parity(outcome, attempt):
    # The buggy version *awarded* +5 for a "Too High" guess on even attempts.
    assert update_score(50, outcome, attempt) == 45

def test_score_is_clamped_at_zero():
    assert update_score(3, "Too Low", 1) == 0

def test_unknown_outcome_leaves_score_untouched():
    assert update_score(42, "Something Else", 1) == 42


# --- Difficulty -------------------------------------------------------------

@pytest.mark.parametrize("difficulty", ["Easy", "Normal", "Hard"])
def test_every_difficulty_has_a_valid_range(difficulty):
    low, high = get_range_for_difficulty(difficulty)
    assert low < high
    assert get_attempt_limit(difficulty) > 0

def test_harder_difficulties_have_wider_ranges():
    # The buggy version made Hard (1-50) narrower than Normal (1-100).
    _, easy_high = get_range_for_difficulty("Easy")
    _, normal_high = get_range_for_difficulty("Normal")
    _, hard_high = get_range_for_difficulty("Hard")
    assert easy_high < normal_high < hard_high

def test_unknown_difficulty_falls_back_to_normal():
    assert get_range_for_difficulty("Impossible") == get_range_for_difficulty("Normal")


# --- Integration: a whole round, no Streamlit required ----------------------

def test_binary_search_always_wins_within_the_attempt_limit():
    """A perfect player must be able to win at every difficulty.

    This is the test that would have caught the unwinnable game.
    """
    for difficulty in ("Easy", "Normal", "Hard"):
        low, high = get_range_for_difficulty(difficulty)
        limit = get_attempt_limit(difficulty)

        for secret in range(low, high + 1):
            lo, hi, attempts, score = low, high, 0, 0
            while attempts < limit:
                guess = (lo + hi) // 2
                attempts += 1
                outcome = check_guess(guess, secret)
                score = update_score(score, outcome, attempts)
                if outcome == "Win":
                    break
                if outcome == "Too High":
                    hi = guess - 1
                else:
                    lo = guess + 1
            else:
                pytest.fail(
                    f"{difficulty}: secret {secret} unwinnable in {limit} attempts"
                )
            assert score >= 10, f"{difficulty}: winning score should be positive"


# --- Challenge 1: advanced edge cases ---------------------------------------
# Three classes of input that still broke the game after the main repair. Each
# was found by probing parse_guess directly, not by reading the code.

# Edge case 1: values too large for CPython to convert.
# int(str) refuses beyond 4300 digits (ValueError), and the old fallback then
# asked float(), which returns inf rather than raising — so a 5000-digit guess
# was reported as "Whole numbers only — no decimals.", which is not true.

def test_absurdly_long_number_is_rejected_as_too_large():
    ok, value, error = parse_guess("9" * 5000, 1, 100)
    assert (ok, value) == (False, None)
    assert error == "That number is far too large."

def test_long_but_convertible_number_is_rejected_as_out_of_range():
    ok, value, error = parse_guess("9" * 100, 1, 100)
    assert (ok, value) == (False, None)
    assert "between 1 and 100" in error


# Edge case 2: float keywords that are not guessable numbers.
# float("inf") and float("nan") both succeed, so these reached the decimal
# branch and produced a message about decimals for input containing no digits.

@pytest.mark.parametrize("raw", ["inf", "-inf", "nan", "Infinity"])
def test_float_keywords_are_not_numbers(raw):
    ok, value, error = parse_guess(raw, 1, 100)
    assert (ok, value) == (False, None)
    assert "is not a number" in error


# Edge case 3: numeric spellings int() accepts but a player never intends.
# PEP 515 lets int("1_0") return 10, and int()/float() accept any Unicode
# decimal digit, so "٤٢" became 42. Both silently produce a different number
# than the one typed.

@pytest.mark.parametrize("raw, would_have_become", [
    ("1_0", 10),            # PEP 515 underscore separator
    ("٤٢", 42),   # Arabic-Indic digits
    ("５０", 50),   # full-width digits
    ("1e3", 1000),          # scientific notation
])
def test_non_plain_digit_spellings_are_rejected_not_reinterpreted(raw, would_have_become):
    ok, value, error = parse_guess(raw, 1, 10000)
    assert ok is False, f"{raw!r} was silently accepted as {would_have_become}"
    assert value is None
    assert error == "Enter the number as plain digits, like 42."


# Whitespace that is not a plain space must still be tolerated, since it is
# usually an artefact of pasting rather than a different number.

@pytest.mark.parametrize("raw", [" 50", "50\n", "\t50 ", "  50  "])
def test_surrounding_whitespace_is_forgiven(raw):
    assert parse_guess(raw, 1, 100) == (True, 50, None)


def test_every_rejection_explains_itself():
    """No input may be rejected with an empty or misleading message."""
    for raw in ["", "   ", None, "abc", "5.9", "inf", "nan", "1_0", "1e3",
                "0", "101", "-7", "9" * 5000]:
        ok, value, error = parse_guess(raw, 1, 100)
        assert ok is False and value is None
        assert error and error.strip(), f"{raw!r} rejected with no message"
        if "decimal" in error.lower():
            assert "." in str(raw), f"{raw!r} wrongly blamed on decimals"
