# Glitch Bot

A mysterious, hacker-inspired autonomous Twitter bot powered by the GAME SDK.

## Setup

1. **Clone the repository and navigate to the project directory:**

   ```sh
   cd /path/to/glitchbot
   ```

2. **Create and activate a virtual environment (recommended):**

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate
   # On Windows: .venv\Scripts\activate
   ```

3. **Upgrade pip (optional but recommended):**

   ```sh
   pip install --upgrade pip
   ```

4. **Install dependencies:**

   ```sh
   pip install -r requirements.txt
   ```

5. **Copy the example environment file and fill in your API keys:**
   ```sh
   cp .env.example .env
   # Edit .env and add your GAME SDK, Twitter, and OpenAI API keys
   ```

## Running the Bot

From the project root, run:

```sh
python -m src.bots.glitch_bot_main
```

## Inspecting the Database

To print the latest database contents:

```sh
python print_db.py
```

Or:

```sh
python -m src.bots.glitch_bot_main printdb
```

## Requirements

- Python 3.9+
- GAME SDK account and API key
- Twitter/X API access
- OpenAI API key (for LLM features)

---

**Tip:** Always activate your virtual environment before running the bot.
