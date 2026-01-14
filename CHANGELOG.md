# Changelog

All notable changes to nothingtoseehere will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-14

### Fixed
- **Critical: Fixed coordinate calculation bug in nodriver integration** 🐛
  - `_get_nodriver_screen_coords()` was double-centering coordinates, causing clicks to be offset by half the element's dimensions
  - Elements are now clicked accurately at their true center position
  - This was causing the "select all" issue - wrong elements were being clicked!

### Added
- **Auto-detection of browser chrome height** 🎯
  - `chrome_height` parameter now optional (defaults to `None`)
  - Automatically detects chrome height using JavaScript: `window.outerHeight - window.innerHeight`
  - Works across all browsers (Chrome, Firefox, Edge, Safari) and operating systems
  - Falls back to 0 for headless/container environments
  - No more manual configuration needed!

- **CDP click fallback option** 🔧
  - Added `use_cdp_click` parameter to `click_nodriver_element()`
  - When enabled, uses Chrome DevTools Protocol for maximum reliability
  - Mouse still moves naturally for visual effect
  - Perfect for: iframes, shadow DOM, overlapping elements

### Changed
- **Improved input clearing with triple-click** 🖱️
  - `fill_nodriver_input()` now uses triple-click instead of global `Cmd+A` / `Ctrl+A`
  - More human-like interaction pattern
  - Only affects the focused element (not the entire page!)
  - Safer when coordinates are slightly off
  - Uses realistic timing between clicks (80-150ms)

- **Updated Wikipedia demo** 📖
  - Added Demo 5: Dark mode toggle
  - Added Demo 6: Custom username search ("Super44")
  - Showcases all new features
  - Updated documentation strings

### Documentation
- Added `IMPROVEMENTS_SUMMARY.md` with detailed explanation of all changes
- Updated README.md with new API examples
- Enhanced example comments to highlight new features

### Compatibility
- ✅ **100% backward compatible** - all existing code works without changes
- All parameters are optional with sensible defaults
- No breaking changes to existing APIs

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
