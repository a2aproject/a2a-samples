# ADK A2A Dice Roll REST Agent Example

This example shows how to build a small **tool-using LLM agent** with the **Google Agent Development Kit (ADK)**, designed to be exposed over REST (and/or A2A).  
The agent:

- Rolls an N-sided dice on request.
- Checks whether numbers are prime using a tool.
- Keeps **conversational state** via in-memory sessions.
- Supports **streaming responses**, suitable for REST, WebSockets, or A2A.

## 1. Prerequisites

- **Python** 3.11 or higher  
  ```bash
  python3 --version
  ```
- **Git** (if you need to clone the repo)  
  ```bash
  git --version
  ```

## 2. Get the Source Code

If you don’t have the repo yet:

```bash
git clone https://github.com/google/a2a-samples.git
cd a2a-samples/samples/python/agents/dice_agent_rest
```

If you already have it:

```bash
cd a2a-samples/samples/python/agents/dice_agent_rest
```


## 3. Create and Activate a Virtual Environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

You should now see `(.venv)` in your terminal prompt.


## 4. Install Dependencies

You can use **`uv`** (if installed) or **`pip`**.

### Option A: Using `uv` (uses `uv.lock`)

From the `dice_agent_rest` directory:

```bash
uv sync
```

(Optional sanity check for uv environment):

```bash
uv run python -c "print('uv environment ready')"
```

### Option B: Using `pip`

Make sure your virtual environment is active (`(.venv)` visible), then run:

```bash
pip install .
```

(Optional, if you want editable mode while developing):

```bash
pip install -e .
```


## 5. Set the Google GenAI API Key

You must set `GOOGLE_API_KEY` before running anything that calls Gemini.

### macOS / Linux

```bash
export GOOGLE_API_KEY="YOUR_API_KEY_HERE"
```

### Windows (PowerShell)

```powershell
setx GOOGLE_API_KEY "YOUR_API_KEY_HERE"
```

Then open a **new** terminal window (for `setx` to take effect) and, if using `venv`, activate it again.

Verify:

```bash
echo $GOOGLE_API_KEY      # macOS / Linux
```

```powershell
echo $Env:GOOGLE_API_KEY  # Windows PowerShell
```


## 6. Environment Sanity Check

With the virtual environment active and dependencies installed:

```bash
python -c "import google.adk, google.genai; print('Environment OK')"
```

If you see `Environment OK` with no errors, the setup is complete.
