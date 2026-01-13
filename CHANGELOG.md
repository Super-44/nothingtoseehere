# Changelog

All notable changes to nothingtoseehere will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-13

### Added
- **Core neuromotor simulation** based on research literature
  - Fitts' Law movement timing (throughput stays under 12 bits/s human ceiling)
  - Minimum Jerk trajectory with asymmetric velocity profiles (peak at 38-45%)
  - Two-component model (ballistic primary + corrective submovements)
  - Signal-dependent noise (scales with velocity)
  - Physiological tremor at 8-12 Hz
  - Realistic path curvature (straightness index 0.80-0.95)
  
- **Mouse control**
  - `move_to()` - Move with human-like kinematics
  - `click()` - Click with log-normal timing
  - `double_click()` - Convenience method
  - `right_click()` - Convenience method  
  - `triple_click()` - Select paragraph/line
  - `hover()` - Move without clicking
  - `scroll()` - Human-like scrolling
  - `drag_to()` - Drag and drop with natural movement
  - `move_relative()` - Move by offset

- **Keyboard control**
  - `type_text()` - Type with realistic inter-key timing and optional typos
  - `press_key()` - Single key press
  - `hotkey()` - Key combinations (Ctrl+C, etc.)

- **Integration helpers**
  - `click_element()` - Click by bounds tuple
  - `fill_input()` - Click and type into input field
  - `click_nodriver_element()` - Direct nodriver element support
  - `fill_nodriver_input()` - Fill nodriver input elements
  - `wait_human()` - Human-like pause

- **Configuration**
  - `NeuromotorConfig` - Full movement configuration
  - `FittsParams` - Fitts' Law coefficients
  - `ClickTimingParams` - Click timing distribution
  - `KeyboardTimingParams` - Typing timing
  - `ReactionTimeParams` - Reaction time distribution

- **Diagnostics**
  - `MovementDiagnostics` - Validate movements are human-plausible

- **Documentation**
  - Comprehensive README with usage examples
  - RESEARCH.md with full statistical reference
  - Example scripts (mouse_demo.py, wikipedia_demo.py)

### Research Basis
Based on peer-reviewed research:
- Fitts (1954) - Information capacity of human motor system
- Flash & Hogan (1985) - Minimum jerk trajectory model
- Meyer et al. (1988) - Two-component submovement model
- van Beers et al. (2004) - Signal-dependent neuromotor noise
