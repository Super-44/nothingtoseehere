# nothingtoseehere - Technical Documentation

A research-grounded Python library for simulating human-like mouse and keyboard input. Nothing to see here, just completely normal human behavior. 🐭

## The Problem

Modern bot detection systems (Cloudflare Turnstile, BeCAPTCHA-Mouse, etc.) don't just check *if* a button was clicked—they analyze *how* the cursor arrived there:

- **Velocity profiles**: Humans have asymmetric bell curves; bots use linear interpolation
- **Throughput**: Human motor system is capped at ~12 bits/second; bots exceed this
- **Path tortuosity**: Humans meander (fractal dimension 1.2-1.4); bots are too straight
- **Spectral analysis**: Humans have 8-12 Hz tremor; bots have flat spectra
- **Click timing**: Humans follow log-normal distributions; bots use uniform random

The old approach of "add some random jitter" fails spectacularly against these systems.

## The Solution

This library implements actual neurophysiology and HCI research:

| Component | Research Basis | Implementation |
|-----------|----------------|----------------|
| Movement timing | Fitts' Law (1954) | `MT = a + b * log₂(2D/W)` with randomized coefficients |
| Trajectory shape | Minimum Jerk Model (Flash & Hogan, 1985) | 5th-order polynomial with asymmetric time warping |
| Submovements | Two-Component Model (Meyer et al., 1988) | Ballistic primary + visually-guided corrections |
| Motor noise | Signal-Dependent Noise (van Beers, 2004) | `σ_noise ∝ velocity` |
| Tremor | Physiological tremor research | Band-pass filtered noise at 8-12 Hz |
| Click timing | HCI empirical studies | Log-normal distribution (μ≈100ms, σ≈25ms) |

## Installation

```bash
pip install numpy scipy pyautogui
```

Then copy the `neuromotor/` package to your project.

## Quick Start

```python
import asyncio
from nothingtoseehere import NeuromotorInput

async def main():
    human = NeuromotorInput()
    
    # Move to button and click (specify target size for Fitts' Law)
    await human.mouse.move_to(500, 300, target_width=100, click=True)
    
    # Type with human-like timing
    await human.keyboard.type_text("Hello, world!")

asyncio.run(main())
```

## Key Features

### 1. Fitts' Law Movement Timing

```python
from nothingtoseehere import FittsLaw, FittsParams

# Configure Fitts' Law parameters
params = FittsParams(
    a_mean=0.300,    # 300ms reaction/preparation
    a_std=0.050,     # ±50ms variation
    b_mean=0.100,    # 100ms per bit of difficulty
    b_std=0.010,     # ±10ms variation
    max_throughput=12.0  # Human ceiling (bits/second)
)

fitts = FittsLaw(params)

# Calculate movement time
distance = 500  # pixels
target_width = 50  # pixels
mt = fitts.movement_time(distance, target_width)
print(f"Expected movement time: {mt*1000:.0f}ms")

# Validate throughput stays human-plausible
is_valid, throughput = fitts.validate_human_plausible(distance, target_width, mt)
print(f"Throughput: {throughput:.1f} bps (valid: {is_valid})")
```

### 2. Asymmetric Velocity Profiles

Real humans reach peak velocity at 38-45% of movement time (not 50%):

```python
from nothingtoseehere import MinimumJerkTrajectory

# Asymmetric profile (peak at 42% of movement)
trajectory = MinimumJerkTrajectory(asymmetry=0.42)

# Generate velocity profile
times, positions, velocities = trajectory.generate_profile(
    duration=0.8,  # 800ms movement
    sample_rate=60.0
)

# Peak occurs at ~42% of duration
peak_idx = velocities.argmax()
peak_time = times[peak_idx] / times[-1]
print(f"Peak velocity at: {peak_time*100:.0f}% of movement")
```

### 3. Two-Component Submovement Model

Movements consist of a fast ballistic phase followed by slower corrections:

```python
from nothingtoseehere import TwoComponentModel

model = TwoComponentModel(
    primary_coverage=0.95,   # Primary covers ~95% of distance
    primary_error_std=0.08,  # 8% std in endpoint
    max_corrections=3        # Up to 3 correction submovements
)

# Plan submovements
submovements = model.plan_submovements(
    start=(100, 100),
    target=(600, 400),
    target_width=50
)

for endpoint, time_fraction in submovements:
    print(f"  → {endpoint} ({time_fraction*100:.0f}% of time)")
```

### 4. Signal-Dependent Neuromotor Noise

Noise scales with movement velocity (faster = shakier):

```python
from nothingtoseehere import NeuromotorNoise

noise = NeuromotorNoise(
    noise_coefficient=0.05,    # σ = 0.05 * velocity
    tremor_frequency=10.0,     # 10 Hz tremor center
    tremor_amplitude=0.5,      # 0.5 pixel RMS
    sample_rate=60.0
)

# Add noise to trajectory
noisy_x, noisy_y = noise.add_noise_to_trajectory(
    positions_x, positions_y, velocities
)
```

### 5. Log-Normal Click Timing

Click durations follow log-normal distribution (not uniform):

```python
from nothingtoseehere import ClickModel, ClickTimingParams

params = ClickTimingParams(
    click_duration_mu=4.6,      # log(100ms)
    click_duration_sigma=0.25,  # ~25ms std
    verification_dwell_mu=5.5,  # ~250ms dwell before click
)

click = ClickModel(params)

# Sample click duration
duration = click.click_duration()
print(f"Click duration: {duration*1000:.0f}ms")

# Verification dwell (human pauses to confirm target)
dwell = click.verification_dwell()
print(f"Pre-click dwell: {dwell*1000:.0f}ms")
```

## Configuration

### Full Configuration Example

```python
from nothingtoseehere import (
    NeuromotorInput,
    NeuromotorConfig,
    FittsParams,
    ClickTimingParams,
    KeyboardTimingParams
)

config = NeuromotorConfig(
    # Fitts' Law parameters
    fitts=FittsParams(
        a_mean=0.300,
        a_std=0.050,
        b_mean=0.100,
        b_std=0.010,
        max_throughput=12.0,
        nominal_error_rate=0.04,
    ),
    
    # Velocity asymmetry (0.38-0.45 for humans)
    velocity_asymmetry=0.42,
    
    # Neuromotor noise
    noise_coefficient=0.05,
    tremor_frequency=10.0,
    tremor_amplitude=0.5,
    
    # Path geometry
    path_curvature=0.15,
    path_deviation=0.10,
    
    # Submovement model
    primary_coverage=0.95,
    primary_error_std=0.08,
    max_corrections=3,
    
    # Sample rate
    sample_rate=60.0,
    
    # Debug mode (slower, more visible)
    debug_mode=False,
)

human = NeuromotorInput(mouse_config=config)
```

### Persona-Based Configuration

Simulate different user types:

```python
# Fast, young gamer
gamer_config = NeuromotorConfig(
    fitts=FittsParams(
        a_mean=0.220,  # Faster reactions
        b_mean=0.085,  # Higher throughput
    ),
    velocity_asymmetry=0.38,  # More aggressive
)

# Older, careful user
elder_config = NeuromotorConfig(
    fitts=FittsParams(
        a_mean=0.450,  # Slower reactions
        b_mean=0.120,  # Lower throughput
        max_throughput=9.0,
    ),
    velocity_asymmetry=0.48,  # More symmetric
    primary_coverage=0.88,    # More corrections needed
)
```

## Validation & Diagnostics

Verify your movements are human-plausible:

```python
from nothingtoseehere import MovementDiagnostics
import numpy as np

diagnostics = MovementDiagnostics()

# Record a trajectory (x, y, timestamps)
x = np.array([...])  # Your x coordinates
y = np.array([...])  # Your y coordinates  
times = np.array([...])  # Timestamps

analysis = diagnostics.analyze_trajectory(
    x, y, times, 
    target_width=50
)

print(f"Throughput: {analysis['throughput_bps']:.1f} bps "
      f"({'✓' if analysis['throughput_valid'] else '✗'})")
print(f"Straightness: {analysis['straightness_index']:.2f} "
      f"({'✓' if analysis['straightness_valid'] else '✗'})")
print(f"Peak velocity at: {analysis['peak_velocity_timing']*100:.0f}% "
      f"({'✓' if analysis['velocity_asymmetry_valid'] else '✗'})")
print(f"Overall: {'PASS' if analysis['overall_valid'] else 'FAIL'}")
```

## Integration with Browser Automation

### With nodriver (Recommended)

The library includes helpers specifically for nodriver with automatic coordinate conversion and page load handling:

```python
from nothingtoseehere import NeuromotorInput
import nodriver as uc

async def automate_with_nodriver():
    human = NeuromotorInput()
    browser = await uc.start()
    page = await browser.get('https://example.com')
    
    # Wait for page load + natural reading time
    await human.wait_for_page(page)
    
    # Click element (automatically converts coordinates and scrolls into view)
    button = await page.select('button.submit')
    await human.click_nodriver_element(button, page)
    
    # Wait for navigation
    await human.wait_for_page(page, min_read_time=0.5, max_read_time=2.0)
    
    # Fill input with human-like typing
    search_box = await page.select('input[name="q"]')
    await human.fill_nodriver_input(
        search_box, page, 
        "search query",
        with_typos=True  # Realistic typos with corrections
    )
```

#### Key nodriver Features:

**Automatic coordinate conversion:**
- Converts element positions to screen coordinates
- Auto-detects browser chrome height
- Accounts for viewport scroll position

**Intelligent page load waiting:**
```python
# Wait for page ready + human reading/orientation time
await human.wait_for_page(page)  # Default: 300-1000ms reading time

# Customize reading time based on content
await human.wait_for_page(page, min_read_time=0.5, max_read_time=2.0)
```

**Automatic scroll into view:**
```python
# Element automatically scrolls into viewport before clicking
await human.click_nodriver_element(element, page, scroll_into_view=True)
```

**Triple-click input clearing:**
```python
# Uses triple-click to clear (more targeted than Cmd+A)
await human.fill_nodriver_input(element, page, "text", clear_first=True)
```

### With Selenium

```python
from nothingtoseehere import NeuromotorInput
from selenium import webdriver

async def click_element(driver, element):
    human = NeuromotorInput()
    
    location = element.location
    size = element.size
    
    await human.mouse.move_to(
        location['x'] + size['width'] // 2,
        location['y'] + size['height'] // 2,
        target_width=size['width'],
        target_height=size['height'],
        click=True
    )
```

## Research References

1. **Fitts, P.M. (1954)**. The information capacity of the human motor system in controlling the amplitude of movement. *Journal of Experimental Psychology*, 47(6), 381-391.

2. **Flash, T., & Hogan, N. (1985)**. The coordination of arm movements: An experimentally confirmed mathematical model. *Journal of Neuroscience*, 5(7), 1688-1703.

3. **Meyer, D.E., et al. (1988)**. Optimality in human motor performance: Ideal control of rapid aimed movements. *Psychological Review*, 95(3), 340-370.

4. **van Beers, R.J., et al. (2004)**. The role of execution noise in movement variability. *Journal of Neurophysiology*, 91(2), 1050-1063.

5. **MacKenzie, I.S. (1992)**. Fitts' law as a research and design tool in human-computer interaction. *Human-Computer Interaction*, 7(1), 91-139.

## Key Statistics Reference

| Metric | Human Range | Bot Signature |
|--------|-------------|---------------|
| Throughput | 8-12 bits/s | >20 bits/s |
| Peak velocity timing | 38-45% | 50% (symmetric) |
| Straightness index | 0.80-0.95 | >0.99 |
| Path RMSE | 10-25 px | ~0 px |
| Tremor frequency | 8-12 Hz | 0 Hz or flat |
| Click duration | 85-130ms (log-normal) | Fixed or uniform |
| Fractal dimension | 1.2-1.4 | 1.0 (linear) |

## License

MIT
