# nothingtoseehere

[![PyPI](https://img.shields.io/pypi/v/nothingtoseehere.svg)](https://pypi.org/project/nothingtoseehere/)
[![Tests](https://github.com/Super-44/nothingtoseehere/actions/workflows/test.yml/badge.svg)](https://github.com/Super-44/nothingtoseehere/actions/workflows/test.yml)
[![Changelog](https://img.shields.io/github/v/release/Super-44/nothingtoseehere?include_prereleases&label=changelog)](https://github.com/Super-44/nothingtoseehere/releases)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/Super-44/nothingtoseehere/blob/main/LICENSE)

A python package that is certainly only for human mouse movement and keyboard input. 🐭

Built on neurophysiology research (Fitts' Law, minimum jerk trajectories, signal-dependent noise) to produce mouse movements and keyboard input that pass behavioral biometric detection.

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

## Development

To contribute to this library, first checkout the code. Then create a new virtual environment:
```bash
cd nothingtoseehere
python -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
python -m pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
