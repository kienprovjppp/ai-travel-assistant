# ✈️ AI Travel Assistant

An AI trip planner built with **Python**, **Streamlit** and the **Claude API**.
Tell it where you're going, your dates, budget and interests. It writes a
day-by-day itinerary with a budget breakdown, checks changing facts (opening
hours, ticket prices, events, entry rules) with live web search, and lets you
refine the plan in a chat.

<!-- Add a screenshot or GIF of the app here: ![demo](docs/demo.png) -->

## Features

- **Personalised itineraries**: destination, dates, group size, budget and currency, interests, pace and free-text notes (diet, kids, mobility...).
- **Live web search**: Claude looks up current prices, opening hours and events instead of relying only on training data.
- **Streaming answers**: the plan appears as it is written, no waiting for the full response.
- **Follow-up chat**: "make day 2 more relaxed", "swap the museum for a beach", "where should I eat near the hotel?". The assistant keeps the whole conversation in context.
- **Budget check**: a cost table per category, with a warning when the budget is unrealistic.
- **Vietnamese or English** output.
- **Export** the whole plan as a Markdown file.

## Tech stack

| Layer | Choice |
|---|---|
| UI | Streamlit (chat elements, forms, `st.write_stream`) |
| LLM | Claude Opus 5.5 through the official `anthropic` Python SDK |
| Grounding | Claude's server-side web search tool |
| Hosting | Streamlit Community Cloud (free) |

## How it works

```mermaid
flowchart LR
    U[Trip form / chat] --> A[app.py]
    A -- streamed request + history --> C[Claude API]
    C -- web_search --> W[(The web)]
    C -- streamed Markdown --> A
    A --> U
```

1. The sidebar form is turned into a structured prompt (`trip_prompt`).
2. `stream_reply` sends the whole conversation to Claude with a system prompt
   that defines the itinerary format, and streams the text back to the page.
3. Claude decides when a fact needs checking and calls the web search tool,
   which runs on Anthropic's servers. Long searches can pause the turn
   (`pause_turn`); the app resumes them automatically.
4. The full assistant turn (including search results) is stored in
   `st.session_state`, so follow-up questions keep their context.

Engineering details worth knowing:

- **Prompt caching** (`cache_control`) re-uses the system prompt and earlier
  turns, which makes follow-up questions cheaper and faster.
- **Error handling** for missing keys, rate limits and network errors. A
  failed turn is removed from the history so the conversation stays valid.
- **Refusal fallback**: if the model declines a request, the API retries it on
  a fallback model in the same call.

## Run it locally

Requirements: Python 3.10+ and an Anthropic API key
([console.anthropic.com](https://console.anthropic.com)).

```bash
git clone https://github.com/kienprovjppp/ai-travel-assistant.git
cd ai-travel-assistant
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...   # macOS/Linux: export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

The app opens at http://localhost:8501.

## Deploy (free)

1. Push this repo to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io), create an app from the repo with `app.py` as the entry point.
3. In **Settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```

Every visitor's request uses your API key, so set a spending limit in the
Anthropic Console before sharing the link.

## Project structure

```
app.py            # the whole app: UI, prompt building, streaming, error handling
test_app.py       # headless UI tests with Streamlit's AppTest
requirements.txt
```

Run the tests with `python test_app.py` (no API key needed).

## Roadmap

- Map view of each day's stops
- Export to PDF / Google Calendar
- Save and share trips (database + login)
- Live flight and hotel prices from a travel API

## License

MIT
