# nothingtoseehere

[![PyPI](https://img.shields.io/pypi/v/nothingtoseehere.svg)](https://pypi.org/project/nothingtoseehere/)
[![Tests](https://github.com/Super-44/nothingtoseehere/actions/workflows/test.yml/badge.svg)](https://github.com/Super-44/nothingtoseehere/actions/workflows/test.yml)
[![Changelog](https://img.shields.io/github/v/release/Super-44/nothingtoseehere?include_prereleases&label=changelog)](https://github.com/Super-44/nothingtoseehere/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/Super-44/nothingtoseehere/blob/main/LICENSE)

A python package that is certainly only for human mouse movement and keyboard input. 🐭

Built on neurophysiology research (Fitts' Law, minimum jerk trajectories, signal-dependent noise) to produce mouse movements and keyboard input that pass behavioral biometric detection.

**Key Statistics** (see [RESEARCH.md](RESEARCH.md) for full details):

| Human Trait | Our Implementation |
|-------------|-------------------|
| Throughput < 12 bits/s | ✓ Enforced |
| Peak velocity at 38-45% | ✓ 42% default |
| Straightness 0.80-0.95 | ✓ ~0.91 |
| 8-12 Hz tremor | ✓ 10 Hz |
| Log-normal clicks ~100ms | ✓ |

## Installation

```bash
pip install nothingtoseehere
```

For browser automation with nodriver:
```bash
pip install nothingtoseehere[browser]
```

## Quick Start

```python
import asyncio
from nothingtoseehere import NeuromotorInput

async def main():
    human = NeuromotorInput()
    
    # Move mouse with human-like kinematics and click
    await human.mouse.move_to(500, 300, target_width=100, click=True)
    
    # Type with realistic timing
    await human.keyboard.type_text("Hello, world!")

asyncio.run(main())
```

## API Overview

### Mouse Methods
```python
await human.mouse.move_to(x, y, target_width=50, click=True)
await human.mouse.hover(x, y)           # Move without clicking
await human.mouse.click()               # Click at current position
await human.mouse.double_click(x, y)    # Double-click
await human.mouse.right_click(x, y)     # Right-click
await human.mouse.triple_click(x, y)    # Select paragraph
await human.mouse.drag_to(x, y)         # Drag and drop
await human.mouse.scroll(-5)            # Scroll down
await human.mouse.move_relative(dx, dy) # Move by offset
```

### Keyboard Methods
```python
await human.keyboard.type_text("Hello!", with_typos=True)
await human.keyboard.press_key("enter")
await human.keyboard.hotkey("ctrl", "c")  # Or "command" on macOS
```

### nodriver Integration
```python
import nodriver as uc
from nothingtoseehere import NeuromotorInput

async def main():
    human = NeuromotorInput()
    browser = await uc.start()
    page = await browser.get("https://example.com")
    
    # Click elements directly - no manual coordinate conversion!
    # Chrome height is auto-detected via JavaScript
    button = await page.select("button.submit")
    await human.click_nodriver_element(button, page)
    
    # For maximum reliability in complex scenarios, use CDP click
    await human.click_nodriver_element(button, page, use_cdp_click=True)
    
    # Fill input fields (uses triple-click for targeted selection)
    search = await page.select("input[name='q']")
    await human.fill_nodriver_input(search, page, "search query")
```

## Demos

Try the interactive demos:

```bash
# Simple mouse movement demo (no browser needed)
python examples/mouse_demo.py

# Browser automation demo with Wikipedia
python examples/wikipedia_demo.py
```

## Documentation

See [nothingtoseehere/README.md](nothingtoseehere/README.md) for detailed documentation on the neuromotor models and configuration options.

## Future Improvements

The following features are planned for future releases:

### Persona Presets
Pre-configured profiles for different user types:
```python
# Coming soon!
human = NeuromotorInput.gamer()     # Fast reactions, high precision
human = NeuromotorInput.elderly()   # Slower, more careful movements
human = NeuromotorInput.mobile()    # Touch-screen patterns
human = NeuromotorInput.novice()    # Hesitant, meandering paths
```

### Device Profiles
- Trackpad simulation (different movement patterns)
- Touch screen gestures
- Gaming mouse profiles

### Recording & Replay
- Record real human movements for analysis
- Replay recorded patterns with variation

## Development

To contribute to this library, first checkout the code. Then create a new virtual environment:
```bash
cd nothingtoseehere
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e ".[dev]"
```
To run the tests:
```bash
python -m pytest
```

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
