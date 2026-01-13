# Research-Grounded Statistics for Human Mouse Movement

This document summarizes the neurophysiology and HCI research that forms the foundation of the `nothingtoseehere` library. All statistics are derived from peer-reviewed research in motor control, human-computer interaction, and behavioral biometrics.

## Quick Reference: Human vs Bot Signatures

| Metric | Human Range | Bot Signature | Our Implementation |
|--------|-------------|---------------|-------------------|
| **Throughput** | 8-12 bits/s | >20 bits/s | ✓ Enforced ceiling |
| **Peak velocity timing** | 38-45% of movement | 50% (symmetric) | ✓ 42% default |
| **Straightness index** | 0.80-0.95 | >0.99 | ✓ ~0.91 |
| **Path RMSE** | 10-25 px | ~0 px | ✓ Realistic deviation |
| **Tremor frequency** | 8-12 Hz | 0 Hz or flat | ✓ 10 Hz peak |
| **Click duration** | 85-130ms (log-normal) | Fixed or uniform | ✓ Log-normal ~100ms |
| **Fractal dimension** | 1.2-1.4 | 1.0 (linear) | ✓ Via micro-corrections |

---

## 1. Fitts' Law: The Speed-Accuracy Tradeoff

The human motor system acts as a communication channel with limited bandwidth. Movement time is governed by:

```
MT = a + b × log₂(2D/W)
```

Where:
- **MT** = Movement Time (seconds)
- **D** = Distance to target (pixels)
- **a** = Intercept (reaction + preparation time)
- **b** = Slope (processing time per bit)
- **log₂(2D/W)** = Index of Difficulty (bits)

### Empirical Coefficients

| Parameter | Value Range | Description |
|-----------|-------------|-------------|
| **a (intercept)** | 0.200-0.500s | Reaction + motor preparation |
| **b (slope)** | 0.090-0.110 s/bit | Processing speed |
| **Throughput** | 8-12 bits/s | Hard physiological ceiling |
| **Error rate** | 4-8% | Probability of missing target |

### Key Insight
A bot moving at constant pixels/second **fails Fitts' Law**. Humans slow down for smaller targets. Any movement exceeding 12 bits/second throughput is flagged as superhuman.

---

## 2. Velocity Profile: The Asymmetric Bell Curve

Human movements follow a **Minimum Jerk** trajectory but with characteristic asymmetry.

### Theoretical vs Real

| Aspect | Theoretical (MJ) | Actual Human |
|--------|------------------|--------------|
| Peak velocity timing | 50% of movement | **38-45%** |
| Profile shape | Symmetric bell | Skewed left |
| Deceleration | Equal to acceleration | **Longer** (visual guidance) |

### The Two Phases

1. **Acceleration (Ballistic)**: Fast, pre-planned, ~95% of distance
2. **Deceleration (Homing)**: Slower, visually-guided corrections

### Peak Velocity
- Peak velocity ≈ **1.875× average velocity**
- For 1000px in 1 second: avg=1000 px/s, peak≈1875 px/s

---

## 3. Submovements: The Micro-Structure

Human movements consist of discrete force pulses called **submovements**.

### Statistics

| Metric | Value |
|--------|-------|
| Submovement count | 90% have <7, most have 1-2 |
| Primary coverage | ~95% of distance |
| Correction probability | ~85% need at least one |
| Overshoot frequency | Dominant on large displays |
| Undershoot frequency | Common for small targets |

### Key Insight
A bot that lands **perfectly on target** with its first movement is statistically improbable. Realistic movement includes an initial endpoint error followed by correction.

---

## 4. Path Geometry: Not a Straight Line

Human paths exhibit characteristic curvature and complexity.

### Metrics

| Metric | Human Range | Robot Value |
|--------|-------------|-------------|
| **Straightness Index** | 0.80-0.95 | 1.0 (perfect) |
| **Fractal Dimension** | 1.2-1.4 | 1.0 (linear) |
| **Path RMSE** | 10-25 pixels | ~0 pixels |
| **Max deviation location** | Near midpoint | N/A |

### Calculation
```
Straightness Index = Straight-line distance / Actual path length
```

### Cognitive Load Effect
Path tortuosity **increases with uncertainty**. A user unsure which button to click shows a "meandering" path (FD closer to 1.4).

---

## 5. Neuromotor Noise: Not White Noise

Human movement noise has specific statistical properties.

### Signal-Dependent Noise (SDN)

The noise scales with movement speed:

```
σ_noise = k × |velocity|
```

- **Implication**: Faster = shakier, slower = steadier
- **k coefficient**: ~0.02 (2% of velocity)

### Physiological Tremor

| Property | Value |
|----------|-------|
| Frequency band | **8-12 Hz** |
| Amplitude (stationary) | <1-5 pixels RMS |
| Amplitude (movement) | ~0.1-0.2 pixels RMS |

### Detection
Bot detectors perform **FFT analysis** on dwell segments looking for the 10Hz tremor peak. A perfectly still cursor (0 Hz) or white noise (flat spectrum) is flagged.

---

## 6. Click Timing: Log-Normal Distribution

Click durations follow a **log-normal** distribution, not uniform random.

### Click Duration (MouseDown → MouseUp)

| Statistic | Value |
|-----------|-------|
| Distribution | Log-Normal |
| Mean | 85-130 ms |
| Std Dev | 20-30 ms |
| Lower bound | 50-60 ms (mechanical limit) |
| Upper bound | 350 ms (long-press threshold) |

### Verification Dwell

Before clicking, humans pause to verify cursor position:
- **Duration**: 200-500 ms
- A bot clicking 0ms after stopping is obvious

### Double-Click Dynamics

| Property | Value |
|----------|-------|
| Inter-click interval | 100-500 ms (mean ~230ms) |
| Spatial drift | 1-5 pixels between clicks |

---

## 7. Reaction Time

Reaction time follows an **Ex-Gaussian** distribution (normal + exponential tail).

| Component | Value |
|-----------|-------|
| Mean RT (visual) | ~230 ms |
| Gaussian μ | ~180 ms |
| Gaussian σ | ~30 ms |
| Exponential τ | ~50 ms |
| Age effect | +2-6 ms per decade |

---

## 8. Bot Detection Features

Modern systems (BeCAPTCHA-Mouse, ReMouse) extract:

### Kinematic Features
- Velocity, acceleration, jerk profiles
- Angular velocity

### Spatial Features  
- Curvature, path tortuosity
- Efficiency indices

### Temporal Features
- Click duration distribution
- Movement time vs ID correlation
- Pause frequency and duration

### Spectral Features
- FFT power in 8-12 Hz band
- Sample entropy

### The "Uncanny Valley"
Detection looks for movements that are **too perfect** or **too random**:
- Straightness Index > 0.99 → suspicious
- Click duration σ < 5ms → suspicious
- Throughput > 12 bits/s → superhuman

---

## References

1. **Fitts, P.M. (1954)**. The information capacity of the human motor system in controlling the amplitude of movement. *Journal of Experimental Psychology*, 47(6), 381-391.

2. **Flash, T., & Hogan, N. (1985)**. The coordination of arm movements: An experimentally confirmed mathematical model. *Journal of Neuroscience*, 5(7), 1688-1703.

3. **Meyer, D.E., et al. (1988)**. Optimality in human motor performance: Ideal control of rapid aimed movements. *Psychological Review*, 95(3), 340-370.

4. **van Beers, R.J., et al. (2004)**. The role of execution noise in movement variability. *Journal of Neurophysiology*, 91(2), 1050-1063.

5. **MacKenzie, I.S. (1992)**. Fitts' law as a research and design tool in human-computer interaction. *Human-Computer Interaction*, 7(1), 91-139.

6. **Woodworth, R.S. (1899)**. The accuracy of voluntary movement. *Psychological Review: Monograph Supplements*, 3(3).

---

## Implementation Checklist

To pass behavioral biometric detection, ensure your implementation:

- [ ] Uses Fitts' Law for movement timing (throughput < 12 bps)
- [ ] Has asymmetric velocity profile (peak at 38-45%)
- [ ] Includes submovements (primary + corrective)
- [ ] Has signal-dependent noise (scales with velocity)
- [ ] Includes 8-12 Hz tremor component
- [ ] Uses log-normal click durations (not uniform)
- [ ] Has verification dwell before clicks (200-500ms)
- [ ] Shows path curvature (straightness 0.80-0.95)
- [ ] Samples endpoints from bivariate normal (not uniform)
- [ ] Occasionally misses targets (~4-8% error rate)
