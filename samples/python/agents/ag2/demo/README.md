# AG2 Demo UI

This folder contains the browser-based WebSocket demo interface for the AG2 A2A sample.

## Files

- **`ui.html`** - Main HTML/CSS/JavaScript for the pixel-art themed demo UI
- **`assets/`** - Visual assets for the interface

## Assets

- `banner.png` - Top title banner (AG2 × A2A)
- `background-clouds.png` - Sky background
- `code-box.png` - Stone frame for code/log panels
- `grass-bottom.png` - Grass strip at the bottom

## How it works

1. The parent folder's `websocket.py` serves this UI at `http://127.0.0.1:9000/`
2. The browser connects via WebSocket to interact with the AG2 agents
3. The UI displays:
   - **Prompt box** - Enter code generation requests
   - **Live Backend Logs** - Real-time status updates and agent conversations
   - **Generated Code** - Final code output after review iterations

## Running the demo

From the parent directory:

```bash
uv run websocket.py
```

Then open `http://127.0.0.1:9000/` in your browser.

## Design notes

The UI uses a retro pixel-art aesthetic inspired by classic RPG games:
- 16-bit style graphics
- Stone-framed panels for content
- Pixel-rendered fonts
- Sky background with grass footer
