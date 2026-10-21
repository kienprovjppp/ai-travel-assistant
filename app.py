"""AI Travel Assistant: plan a trip with Claude, then refine it in chat."""

import os
from datetime import date, timedelta

import anthropic
import streamlit as st

MODEL = "claude-opus-5-5"
SYSTEM = """You are an expert travel planner.

When asked for a trip plan, write a day-by-day itinerary in Markdown:
- A short trip overview (best area to stay, getting around, weather/season notes).
- One `### Day N` section per day with morning / afternoon / evening, each with
  a specific place, why it fits the traveler, and a rough cost.
- A budget table (accommodation, food, transport, activities, total) in the
  traveler's currency, and say clearly if the budget is unrealistic.
- Practical tips: visas/entry, local customs, scams to avoid, what to book early.

Use web search to check facts that change: opening hours, ticket prices,
events on the travel dates, entry requirements. Never invent a place.
For follow-up questions, change only what the traveler asks about and keep
the rest of the plan consistent. Reply in the language the traveler asks for."""
# Server-side tool: Anthropic runs the searches, no client code needed.
TOOLS = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}]
INTERESTS = ["Food", "Culture & history", "Nature", "Beaches", "Nightlife",
             "Shopping", "Adventure", "Photography", "Family-friendly"]


@st.cache_resource
def get_client() -> anthropic.Anthropic:
    # Reads ANTHROPIC_API_KEY from the environment (or Streamlit Cloud secrets).
    return anthropic.Anthropic()


def trip_prompt(*, destination, origin, start, days, travelers, budget,
                currency, interests, pace, notes, language) -> str:
    end = start + timedelta(days=days - 1)
    lines = [
        f"Plan a {days}-day trip to {destination} for {travelers} traveler(s).",
        f"Dates: {start:%d %b %Y} to {end:%d %b %Y}.",
        f"Total budget: {budget:,.0f} {currency}, excluding flights from {origin}."
        if origin else f"Total budget: {budget:,.0f} {currency}.",
        f"Interests: {', '.join(interests) or 'a bit of everything'}.",
        f"Pace: {pace}.",
    ]
    if notes:
        lines.append(f"Other notes: {notes}")
    lines.append(f"Write the whole answer in {language}.")
    return "\n".join(lines)


def stream_reply(messages: list):
    """Yield Claude's text as it arrives and append the assistant turn to `messages`."""
    while True:
        with get_client().beta.messages.stream(
            model=MODEL,
            max_tokens=32000,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
            cache_control={"type": "ephemeral"},
            # If Claude declines, the API retries on a fallback model in the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        ) as stream:
            yield from stream.text_stream
            message = stream.get_final_message()
        # Keep the full content (search results, thinking) so the next turn has it.
        messages.append({"role": "assistant", "content": message.content})
        if message.stop_reason == "pause_turn":  # long web search: let Claude continue
            continue
        if message.stop_reason == "refusal":
            yield "\n\n_Sorry, I can't help with that request._"
        elif message.stop_reason == "max_tokens":
            yield "\n\n_The answer was cut off. Ask me to continue._"
        return


def respond(prompt: str, shown: str) -> None:
    """Send `prompt` to Claude, show `shown` as the user's bubble, stream the reply."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.chat.append(("user", shown))
    with st.chat_message("user"):
        st.markdown(shown)
    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(stream_reply(st.session_state.messages))
        except anthropic.AuthenticationError:
            st.error("The API key was rejected. Check `ANTHROPIC_API_KEY` and restart the app.")
        except anthropic.RateLimitError:
            st.error("Rate limited. Wait a minute and try again.")
        except anthropic.APIConnectionError:
            st.error("Can't reach the Claude API. Check your internet connection.")
        except anthropic.AnthropicError as e:
            st.error(f"Claude API error: {e}")
        else:
            st.session_state.chat.append(("assistant", reply))
            return
    # Failed turn: drop the unanswered prompt so the history stays valid.
    while st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        st.session_state.messages.pop()
    st.session_state.chat.pop()


st.set_page_config(page_title="AI Travel Assistant", page_icon="✈️", layout="wide")
st.session_state.setdefault("messages", [])  # what Claude sees
st.session_state.setdefault("chat", [])      # what the user sees: (role, text)

with st.sidebar:
    st.header("Your trip")
    with st.form("trip"):
        destination = st.text_input("Destination", placeholder="Da Nang, Vietnam")
        origin = st.text_input("Travelling from (optional)", placeholder="Ho Chi Minh City")
        start = st.date_input("Start date", date.today() + timedelta(days=30))
        days = st.number_input("Days", 1, 30, 4)
        travelers = st.number_input("Travelers", 1, 20, 2)
        c1, c2 = st.columns([3, 2])
        budget = c1.number_input("Budget", 0, value=15_000_000, step=500_000)
        currency = c2.selectbox("Currency", ["VND", "USD", "EUR", "JPY", "KRW", "THB"])
        interests = st.multiselect("Interests", INTERESTS, ["Food", "Culture & history"])
        pace = st.select_slider("Pace", ["Relaxed", "Balanced", "Packed"], "Balanced")
        notes = st.text_area("Anything else?", placeholder="Vegetarian, travelling with a toddler...")
        language = st.radio("Answer in", ["Tiếng Việt", "English"], horizontal=True)
        submitted = st.form_submit_button("Plan my trip", type="primary", use_container_width=True)
    if st.session_state.chat and st.button("Start over", use_container_width=True):
        st.session_state.messages, st.session_state.chat = [], []
        st.rerun()

st.title("✈️ AI Travel Assistant")
st.caption("Day-by-day itineraries with live web search, powered by Claude.")

# Without a key the SDK raises a bare TypeError on the first request, so check up front.
if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
    st.error("Set the `ANTHROPIC_API_KEY` environment variable (or Streamlit secret) "
             "and restart the app. Get a key at https://console.anthropic.com.")
    st.stop()

if not st.session_state.chat and not submitted:
    st.info("Fill in your trip on the left and press **Plan my trip**. "
            "Then ask follow-ups, like *make day 2 more relaxed* or *find vegan food near my hotel*.")

for role, text in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)

if submitted:
    if not destination.strip():
        st.sidebar.error("Enter a destination.")
    else:
        st.session_state.messages, st.session_state.chat = [], []
        respond(
            trip_prompt(destination=destination.strip(), origin=origin.strip(), start=start,
                        days=int(days), travelers=int(travelers), budget=budget,
                        currency=currency, interests=interests, pace=pace,
                        notes=notes.strip(), language=language),
            f"Plan a {int(days)}-day trip to **{destination.strip()}**.",
        )

if st.session_state.chat:
    if question := st.chat_input("Ask about your trip..."):
        respond(question, question)
    st.download_button("Download trip plan (.md)", "\n\n---\n\n".join(
        text for _, text in st.session_state.chat), "trip-plan.md")
