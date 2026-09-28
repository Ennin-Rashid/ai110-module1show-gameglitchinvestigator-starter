"""Streamlit UI for the Number Guessing Game.

This module owns presentation and session state only. All game rules live in
`logic_utils.py` so they can be unit tested without a running Streamlit server.
"""

import random

import streamlit as st

from logic_utils import (
    WIN,
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    hint_for,
    parse_guess,
    update_score,
)

PLAYING = "playing"
WON = "won"
LOST = "lost"


def start_new_round(difficulty: str, reset_score: bool = True) -> None:
    """Reset every piece of round state for a fresh game.

    The original bug was that "New Game" reset only `attempts` and `secret`,
    leaving `status` at "won"/"lost" forever — so the game could never be
    restarted once it ended.
    """
    low, high = get_range_for_difficulty(difficulty)
    st.session_state.difficulty = difficulty
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.status = PLAYING
    st.session_state.history = []
    st.session_state.last_feedback = None
    st.session_state.celebrated = False
    if reset_score:
        st.session_state.score = 0


st.set_page_config(page_title="Number Guessing Game", page_icon="🎮")

st.title("🎮 Number Guessing Game")
st.caption("Guess the secret number before you run out of attempts.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

low, high = get_range_for_difficulty(difficulty)
attempt_limit = get_attempt_limit(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

# First run of the session.
if "secret" not in st.session_state:
    start_new_round(difficulty)

# Changing difficulty changes the valid range, so the old secret may now be
# unreachable. Start a fresh round instead of leaving a stale secret behind.
if st.session_state.difficulty != difficulty:
    start_new_round(difficulty)
    st.info(f"Difficulty changed to {difficulty}. New round started.")

attempts_left = attempt_limit - st.session_state.attempts

left, right = st.columns(2)
left.metric("Score", st.session_state.score)
right.metric("Attempts left", max(0, attempts_left))

if st.button("New Game 🔁"):
    start_new_round(difficulty)
    st.rerun()

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts used:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Status:", st.session_state.status)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)

if st.session_state.status == WON:
    # Only once per round: the win screen reruns whenever the player
    # touches the expander or the sidebar.
    if not st.session_state.celebrated:
        st.balloons()
        st.session_state.celebrated = True
    st.success(
        f"🎉 You won! The secret was {st.session_state.secret}. "
        f"Final score: {st.session_state.score}"
    )
    st.info("Press **New Game 🔁** to play again.")
    st.stop()

if st.session_state.status == LOST:
    st.error(
        f"Out of attempts! The secret was {st.session_state.secret}. "
        f"Final score: {st.session_state.score}"
    )
    st.info("Press **New Game 🔁** to try again.")
    st.stop()

st.subheader("Make a guess")
st.info(f"Guess a whole number between {low} and {high}. Attempts left: {attempts_left}")

if st.session_state.last_feedback:
    st.warning(st.session_state.last_feedback)

show_hint = st.checkbox("Show higher/lower hints", value=True)

with st.form("guess_form", clear_on_submit=True):
    raw_guess = st.text_input("Enter your guess:")
    submit = st.form_submit_button("Submit Guess 🚀")

if submit:
    ok, guess, error = parse_guess(raw_guess, low, high)

    if not ok:
        # An invalid entry is a typo, not a turn. Don't burn an attempt on it.
        st.error(error)
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess)

        outcome = check_guess(guess, st.session_state.secret)
        st.session_state.score = update_score(
            current_score=st.session_state.score,
            outcome=outcome,
            attempt_number=st.session_state.attempts,
        )

        if outcome == WIN:
            st.session_state.status = WON
        elif st.session_state.attempts >= attempt_limit:
            st.session_state.status = LOST
        elif show_hint:
            st.session_state.last_feedback = f"{guess} — {hint_for(outcome)}"
        else:
            st.session_state.last_feedback = f"{guess} is not it. Try again."

        # Rerun unconditionally: the score and attempts-left metrics are drawn
        # above this handler, so without a rerun they would show the state from
        # before this guess.
        st.rerun()

if st.session_state.history:
    st.caption("Your guesses: " + ", ".join(str(g) for g in st.session_state.history))

st.divider()
st.caption("Logic lives in logic_utils.py and is covered by tests/test_game_logic.py.")
