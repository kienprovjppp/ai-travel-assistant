"""Headless smoke tests for app.py. Run: python test_app.py (no real API key needed)."""

import os

from streamlit.testing.v1 import AppTest


def run_app(key: str | None) -> AppTest:
    os.environ.pop("ANTHROPIC_API_KEY", None)
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    return AppTest.from_file("app.py", default_timeout=60).run()


def test_missing_key_shows_setup_message():
    at = run_app(None)
    assert "ANTHROPIC_API_KEY" in at.error[0].value


def test_empty_destination_is_rejected():
    at = run_app("sk-ant-fake")
    at.button[0].click().run()
    assert at.error[0].value == "Enter a destination."


def test_bad_key_shows_error_and_keeps_history_clean():
    # Sends a real request; the API answers 401 for the fake key.
    at = run_app("sk-ant-fake")
    at.sidebar.text_input[0].input("Da Nang, Vietnam")
    at.button[0].click().run()
    assert not at.exception, at.exception
    assert "API key was rejected" in at.error[0].value
    assert at.session_state.messages == [] and at.session_state.chat == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
