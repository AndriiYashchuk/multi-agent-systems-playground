# Multi-Agent Systems Playground

A playground for experimenting with multi-agent systems using LangChain.

## Setup

1. **Create a virtual environment:**

```bash
python -m venv .venv
```

2. **Activate it:**

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Run

```bash
python -m playground.main
```

## Project Structure

```
src/playground/
├── __init__.py
├── config.py      # Settings via pydantic-settings
└── main.py        # Entry point
```
