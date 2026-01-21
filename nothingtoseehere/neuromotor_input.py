"""
nothingtoseehere - Core Implementation

A research-grounded implementation of human-like mouse and keyboard input.
Based on neurophysiology, HCI research, and behavioral biometrics literature.

Key features:
- Fitts' Law movement timing with proper coefficients
- Minimum Jerk trajectory planning with asymmetric velocity profiles
- Two-component model (ballistic + corrective submovements)
- Signal-dependent noise scaled by velocity
- Physiological tremor at 8-12 Hz
- Log-normal click duration distributions
- Path tortuosity and fractal dimension matching
- Throughput validation (stays under 12 bits/s human ceiling)

References:
- Fitts (1954): Information capacity of human motor system
- Flash & Hogan (1985): Minimum jerk model
- Meyer et al. (1988): Optimized submovement model
- van Beers et al. (2004): Signal-dependent noise in motor control
"""

import asyncio
import math
import platform
import random
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Any, Literal
import numpy as np
from scipy import signal as scipy_signal
from scipy.stats import lognorm
import pyautogui

# =============================================================================
# CONSTANTS
# =============================================================================

# Platform detection
IS_MACOS = platform.system() == 'Darwin'
MODIFIER_KEY = 'command' if IS_MACOS else 'ctrl'

# Type aliases
ButtonType = Literal['left', 'right', 'middle']

# Research-derived constants
EFFECTIVE_WIDTH_CONSTANT = 4.133  # Captures 96% of hits (We = 4.133 * σ)
HUMAN_THROUGHPUT_CEILING = 12.0  # bits/second - hard physiological limit
MIN_MOVEMENT_DISTANCE = 3  # pixels - below this, no movement needed
MIN_SUBMOVEMENT_DISTANCE = 5  # pixels - threshold for submovement planning

# Timing constants (seconds)
MIN_CLICK_DURATION = 0.050  # Physical minimum
MAX_CLICK_DURATION = 0.350  # Before it's considered a long-press
MIN_REACTION_TIME = 0.100  # Absolute minimum human RT
MIN_INTER_KEY_INTERVAL = 0.030  # Physical typing minimum

# PyAutoGUI configuration
# Set FAILSAFE=False for automation (move mouse to corner won't abort)
# Set PAUSE=0 for no artificial delays (we add our own human-like delays)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


# =============================================================================
# STATISTICAL DISTRIBUTIONS
# =============================================================================

class Distributions:
    """
    Human-realistic statistical distributions for timing and positioning.
    Based on empirical research data.
    """
    
    @staticmethod
    def log_normal(mu: float, sigma: float) -> float:
        """
        Sample from log-normal distribution.
        Used for click durations, dwell times, reaction times.
        
        The log-normal captures the characteristic "sharp rise, fat tail"
        of human response time distributions.
        """
        # scipy's lognorm uses shape (s) and scale parameters
        # For target mu, sigma of the log: scale=exp(mu), s=sigma
        return float(lognorm.rvs(s=sigma, scale=np.exp(mu)))
    
    @staticmethod
    def ex_gaussian(mu: float, sigma: float, tau: float) -> float:
        """
        Ex-Gaussian distribution (normal convolved with exponential).
        Best model for reaction times.
        
        mu, sigma: parameters of the Gaussian component
        tau: rate parameter of exponential tail
        """
        gaussian_part = random.gauss(mu, sigma)
        exponential_part = random.expovariate(1 / tau) if tau > 0 else 0
        return max(0, gaussian_part + exponential_part)
    
    @staticmethod
    def truncated_normal(mu: float, sigma: float, lower: float, upper: float) -> float:
        """Normal distribution truncated to bounds."""
        for _ in range(100):  # Rejection sampling
            val = random.gauss(mu, sigma)
            if lower <= val <= upper:
                return val
        return np.clip(random.gauss(mu, sigma), lower, upper)
    
    @staticmethod
    def bivariate_normal(
        center: Tuple[float, float],
        sigma_x: float,
        sigma_y: float,
        correlation: float = 0.0
    ) -> Tuple[float, float]:
        """
        Sample from 2D Gaussian for endpoint distribution.
        Used for click targeting with realistic spread.
        """
        # Generate correlated samples
        z1 = random.gauss(0, 1)
        z2 = random.gauss(0, 1)
        
        x = center[0] + sigma_x * z1
        y = center[1] + sigma_y * (correlation * z1 + math.sqrt(1 - correlation**2) * z2)
        
        return (x, y)


# =============================================================================
# FITTS' LAW CALCULATIONS
# =============================================================================

@dataclass
class FittsParams:
    """
    Fitts' Law parameters with realistic variation.
    
    Research values:
    - a (intercept): 200-500ms (reaction/preparation time)
    - b (slope): 90-110 ms/bit (processing speed)
    - Throughput: 8-12 bits/s (human bandwidth ceiling)
    """
    # Intercept: includes reaction time + motor preparation
    a_mean: float = 0.300  # 300ms
    a_std: float = 0.050   # ±50ms variation
    
    # Slope: time per bit of difficulty
    b_mean: float = 0.100  # 100 ms/bit
    b_std: float = 0.010   # ±10ms variation
    
    # Human throughput ceiling (bits per second)
    max_throughput: float = 12.0
    
    # Error rate (probability of missing target)
    nominal_error_rate: float = 0.04  # 4%
    
    def sample_coefficients(self) -> Tuple[float, float]:
        """Get randomized a, b coefficients for this movement."""
        a = max(0.15, random.gauss(self.a_mean, self.a_std))
        b = max(0.06, random.gauss(self.b_mean, self.b_std))
        return a, b


class FittsLaw:
    """
    Fitts' Law calculator for movement time prediction.
    
    MT = a + b * log2(2D/W)
    
    Where:
    - MT: Movement time (seconds)
    - D: Distance to target center (pixels)
    - W: Target width (pixels)
    - a: Intercept (preparation time)
    - b: Slope (processing time per bit)
    """
    
    def __init__(self, params: Optional[FittsParams] = None):
        self.params = params or FittsParams()
    
    def index_of_difficulty(self, distance: float, width: float) -> float:
        """
        Calculate Index of Difficulty (ID) in bits.
        
        ID = log2(2D/W)
        """
        if width <= 0:
            width = 1  # Prevent division by zero
        if distance <= 0:
            return 0.5  # Minimum ID for very short movements
        
        return math.log2(2 * distance / width)
    
    def movement_time(
        self,
        distance: float,
        width: float,
        a: Optional[float] = None,
        b: Optional[float] = None
    ) -> float:
        """
        Calculate expected movement time.
        
        Args:
            distance: Distance to target (pixels)
            width: Target width (pixels)
            a, b: Fitts coefficients (randomized if not provided)
        
        Returns:
            Movement time in seconds
        """
        if a is None or b is None:
            a, b = self.params.sample_coefficients()
        
        id_bits = self.index_of_difficulty(distance, width)
        mt = a + b * id_bits
        
        # Ensure we don't exceed human throughput ceiling
        min_time = id_bits / self.params.max_throughput
        mt = max(mt, min_time)
        
        return mt
    
    def effective_width(self, target_width: float) -> float:
        """
        Calculate effective width (We) for endpoint distribution.
        
        We = 4.133 * σ (captures 96% of hits)
        Therefore: σ = We / 4.133 ≈ target_width / 4.133
        
        This gives the standard deviation for bivariate normal
        endpoint sampling.
        """
        return target_width / EFFECTIVE_WIDTH_CONSTANT
    
    def throughput(self, distance: float, width: float, time: float) -> float:
        """
        Calculate achieved throughput (bits/second).
        
        Used to validate that movements stay within human limits.
        """
        if time <= 0:
            return float('inf')
        id_bits = self.index_of_difficulty(distance, width)
        return id_bits / time
    
    def validate_human_plausible(
        self,
        distance: float,
        width: float,
        time: float
    ) -> Tuple[bool, float]:
        """
        Check if a movement is plausibly human.
        
        Returns:
            (is_valid, throughput) - True if throughput < 12 bps
        """
        tp = self.throughput(distance, width, time)
        return tp <= self.params.max_throughput, tp


# =============================================================================
# MINIMUM JERK TRAJECTORY MODEL
# =============================================================================

class MinimumJerkTrajectory:
    """
    Minimum Jerk trajectory generator.
    
    The CNS plans movements to minimize jerk (rate of change of acceleration).
    This produces characteristic smooth, bell-shaped velocity profiles.
    
    Key modification: Real human movements are ASYMMETRIC.
    Peak velocity occurs at 38-45% of movement time (not 50%).
    """
    
    def __init__(self, asymmetry: float = 0.40):
        """
        Args:
            asymmetry: Time fraction for peak velocity (0.38-0.45 for humans)
        """
        self.asymmetry = asymmetry
    
    def position(self, t: float, duration: float) -> float:
        """
        Normalized position (0 to 1) at time t.
        
        Using minimum jerk polynomial:
        x(τ) = 10τ³ - 15τ⁴ + 6τ⁵
        where τ = t/T
        """
        if duration <= 0:
            return 1.0
        
        tau = np.clip(t / duration, 0, 1)
        
        # Apply asymmetry by warping time
        tau = self._warp_time(tau)
        
        return 10 * tau**3 - 15 * tau**4 + 6 * tau**5
    
    def velocity(self, t: float, duration: float) -> float:
        """
        Normalized velocity at time t.
        
        v(τ) = (30τ² - 60τ³ + 30τ⁴) / T
        
        Peak is 1.875 times average velocity.
        """
        if duration <= 0:
            return 0.0
        
        tau = np.clip(t / duration, 0, 1)
        tau = self._warp_time(tau)
        
        # Derivative of position polynomial
        return (30 * tau**2 - 60 * tau**3 + 30 * tau**4) / duration
    
    def _warp_time(self, tau: float) -> float:
        """
        Warp normalized time to create asymmetric velocity profile.
        
        Uses a sigmoid-based warp to shift peak velocity earlier:
        - asymmetry < 0.5: peak comes earlier (acceleration-dominant)
        - asymmetry = 0.5: symmetric (theoretical minimum jerk)
        - asymmetry > 0.5: peak comes later (deceleration-dominant)
        
        Human movements are acceleration-dominant (asymmetry ≈ 0.40)
        """
        if abs(self.asymmetry - 0.5) < 0.01:
            return tau
        
        # Use a simple polynomial warp that shifts the midpoint
        # The peak of velocity profile occurs where d²x/dt² = 0
        # which for minimum jerk is at t = 0.5 in original time
        # We want to map 0.5 -> asymmetry
        
        # Cubic warp: keeps endpoints fixed, shifts midpoint
        # tau_warped = tau + k * tau * (1 - tau) * (0.5 - tau)
        # where k controls the shift amount
        
        # Calculate k to shift 0.5 to self.asymmetry approximately
        # Using a simpler approach: power-based stretch
        if self.asymmetry < 0.5:
            # Stretch early part, compress late part
            power = math.log(0.5) / math.log(self.asymmetry)
            return tau ** power
        else:
            # Compress early part, stretch late part
            power = math.log(0.5) / math.log(1 - self.asymmetry)
            return 1 - (1 - tau) ** power
    
    def generate_profile(
        self,
        duration: float,
        sample_rate: float = 60.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate complete position and velocity profiles.
        
        Returns:
            times, positions (0-1), velocities
        """
        n_samples = max(2, int(duration * sample_rate))
        times = np.linspace(0, duration, n_samples)
        
        positions = np.array([self.position(t, duration) for t in times])
        velocities = np.array([self.velocity(t, duration) for t in times])
        
        return times, positions, velocities


# =============================================================================
# NEUROMOTOR NOISE MODEL
# =============================================================================

class NeuromotorNoise:
    """
    Signal-dependent neuromotor noise with physiological tremor.
    
    Key insight: Noise in the motor system scales with control signal magnitude.
    σ_noise ∝ |velocity|
    
    Additionally, there's a physiological tremor component at 8-12 Hz.
    """
    
    def __init__(
        self,
        noise_coefficient: float = 0.02,
        tremor_frequency: float = 10.0,
        tremor_amplitude: float = 0.15,
        sample_rate: float = 60.0
    ):
        """
        Args:
            noise_coefficient: k in σ = k * |v| (0.02 = 2% of velocity, realistic)
            tremor_frequency: Center frequency of tremor (Hz)
            tremor_amplitude: RMS amplitude of tremor (pixels, 0.1-0.2 is human range)
            sample_rate: Samples per second
        """
        self.noise_coefficient = noise_coefficient
        self.tremor_frequency = tremor_frequency
        self.tremor_amplitude = tremor_amplitude
        self.sample_rate = sample_rate
        
        # Tremor bandwidth (±2 Hz around center)
        self.tremor_bandwidth = 2.0
    
    def signal_dependent_noise(self, velocity: float) -> float:
        """
        Generate noise scaled by current velocity.
        
        σ = k * |v|
        """
        sigma = self.noise_coefficient * abs(velocity)
        return random.gauss(0, max(0.1, sigma))
    
    def generate_tremor(self, n_samples: int) -> np.ndarray:
        """
        Generate physiological tremor signal at 8-12 Hz.
        
        Uses band-pass filtered noise to create realistic tremor spectrum.
        """
        if n_samples < 4:
            return np.zeros(n_samples)
        
        # Generate white noise
        white_noise = np.random.randn(n_samples)
        
        # Design band-pass filter for tremor frequency
        nyquist = self.sample_rate / 2
        low = (self.tremor_frequency - self.tremor_bandwidth) / nyquist
        high = (self.tremor_frequency + self.tremor_bandwidth) / nyquist
        
        # Clamp to valid range
        low = max(0.01, min(0.99, low))
        high = max(low + 0.01, min(0.99, high))
        
        try:
            b, a = scipy_signal.butter(2, [low, high], btype='band')
            tremor = scipy_signal.filtfilt(b, a, white_noise)
        except ValueError:
            # Fallback if filter design fails
            tremor = white_noise * 0.1
        
        # Scale to desired amplitude
        if np.std(tremor) > 0:
            tremor = tremor / np.std(tremor) * self.tremor_amplitude
        
        return tremor
    
    def add_noise_to_trajectory(
        self,
        positions_x: np.ndarray,
        positions_y: np.ndarray,
        velocities: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Add neuromotor noise to a trajectory.
        
        Combines:
        1. Signal-dependent noise (scaled by velocity)
        2. Physiological tremor (8-12 Hz component)
        
        Returns:
            Noisy (x, y) positions
        """
        n = len(positions_x)
        
        # Generate tremor components
        tremor_x = self.generate_tremor(n)
        tremor_y = self.generate_tremor(n)
        
        # Add signal-dependent noise at each point
        noisy_x = np.zeros(n)
        noisy_y = np.zeros(n)
        
        for i in range(n):
            v = velocities[i] if i < len(velocities) else 0
            
            # Signal-dependent component
            sd_noise_x = self.signal_dependent_noise(v)
            sd_noise_y = self.signal_dependent_noise(v)
            
            # Combine position + signal-dependent + tremor
            noisy_x[i] = positions_x[i] + sd_noise_x + tremor_x[i]
            noisy_y[i] = positions_y[i] + sd_noise_y + tremor_y[i]
        
        return noisy_x, noisy_y


# =============================================================================
# TWO-COMPONENT SUBMOVEMENT MODEL
# =============================================================================

class TwoComponentModel:
    """
    Meyer et al. (1988) Optimized Submovement Model.
    
    Movements consist of:
    1. Primary submovement (ballistic, ~95% of distance)
    2. Optional corrective submovements (visually guided)
    
    Key statistics:
    - 90% of movements have <7 submovements
    - Most have just 1 (primary) or 2 (primary + 1 correction)
    - Primary movement undershoots in 90%+ of cases
    - Corrections are shorter and slower
    """
    
    def __init__(
        self,
        primary_coverage: float = 0.95,
        primary_error_std: float = 0.08,
        correction_probability: float = 0.85,
        max_corrections: int = 3,
        # Primary submovement timing (fraction of total time)
        primary_time_range: Tuple[float, float] = (0.70, 0.85),
        # Correction timing (fraction of remaining time)
        correction_time_range: Tuple[float, float] = (0.4, 0.7),
        # Gain limits for primary (allows overshoot up to 15%)
        primary_gain_range: Tuple[float, float] = (0.7, 1.15),
        # Lateral error as fraction of distance
        lateral_error_fraction: float = 0.03,
    ):
        """
        Args:
            primary_coverage: Fraction of distance covered by primary (0.90-0.98)
            primary_error_std: Std dev of primary endpoint as fraction of distance
            correction_probability: Probability of needing correction
            max_corrections: Maximum number of corrective submovements
            primary_time_range: (min, max) fraction of total time for primary
            correction_time_range: (min, max) fraction of remaining time per correction
            primary_gain_range: (min, max) gain for primary (>1 = overshoot)
            lateral_error_fraction: Lateral error std as fraction of distance
        """
        self.primary_coverage = primary_coverage
        self.primary_error_std = primary_error_std
        self.correction_probability = correction_probability
        self.max_corrections = max_corrections
        self.primary_time_range = primary_time_range
        self.correction_time_range = correction_time_range
        self.primary_gain_range = primary_gain_range
        self.lateral_error_fraction = lateral_error_fraction
    
    def plan_submovements(
        self,
        start: Tuple[float, float],
        target: Tuple[float, float],
        target_width: float
    ) -> List[Tuple[Tuple[float, float], float]]:
        """
        Plan a sequence of submovements from start to target.
        
        Returns:
            List of (endpoint, relative_duration) tuples
        """
        distance = math.sqrt(
            (target[0] - start[0])**2 + (target[1] - start[1])**2
        )
        
        if distance < MIN_SUBMOVEMENT_DISTANCE:
            # Too close for submovements
            return [(target, 1.0)]
        
        submovements = []
        current_pos = start
        remaining_time_fraction = 1.0
        
        # Primary submovement (ballistic)
        primary_endpoint, primary_error = self._generate_primary(
            current_pos, target, distance
        )
        
        # Primary takes majority of time
        primary_time = random.uniform(*self.primary_time_range)
        submovements.append((primary_endpoint, primary_time))
        remaining_time_fraction -= primary_time
        current_pos = primary_endpoint
        
        # Corrective submovements
        error_distance = math.sqrt(
            (target[0] - current_pos[0])**2 + 
            (target[1] - current_pos[1])**2
        )
        
        correction_count = 0
        while (
            error_distance > target_width * 0.3 and
            correction_count < self.max_corrections and
            random.random() < self.correction_probability and
            remaining_time_fraction > 0.05
        ):
            correction_endpoint, _ = self._generate_correction(
                current_pos, target, error_distance
            )
            
            # Each correction takes a fraction of remaining time
            correction_time = remaining_time_fraction * random.uniform(*self.correction_time_range)
            submovements.append((correction_endpoint, correction_time))
            remaining_time_fraction -= correction_time
            
            current_pos = correction_endpoint
            error_distance = math.sqrt(
                (target[0] - current_pos[0])**2 + 
                (target[1] - current_pos[1])**2
            )
            correction_count += 1
        
        # Final correction to target (if needed)
        if error_distance > 1:
            submovements.append((target, remaining_time_fraction))
        
        return submovements
    
    def _generate_primary(
        self,
        start: Tuple[float, float],
        target: Tuple[float, float],
        distance: float
    ) -> Tuple[Tuple[float, float], float]:
        """
        Generate primary (ballistic) submovement endpoint.
        
        Typically undershoots by ~5% with some lateral error.
        """
        dx = target[0] - start[0]
        dy = target[1] - start[1]
        
        # Gain: how much of the distance we cover (typically undershoots)
        gain = random.gauss(self.primary_coverage, self.primary_error_std)
        gain = np.clip(gain, *self.primary_gain_range)
        
        # Lateral error (perpendicular to movement direction)
        lateral_error = random.gauss(0, distance * self.lateral_error_fraction)
        
        # Calculate endpoint
        if distance > 0:
            perp_x = -dy / distance
            perp_y = dx / distance
        else:
            perp_x, perp_y = 0, 0
        
        endpoint_x = start[0] + dx * gain + perp_x * lateral_error
        endpoint_y = start[1] + dy * gain + perp_y * lateral_error
        
        # Calculate actual error
        error = math.sqrt(
            (target[0] - endpoint_x)**2 + (target[1] - endpoint_y)**2
        )
        
        return (endpoint_x, endpoint_y), error
    
    def _generate_correction(
        self,
        current: Tuple[float, float],
        target: Tuple[float, float],
        current_error: float
    ) -> Tuple[Tuple[float, float], float]:
        """
        Generate corrective submovement.
        
        Corrections are more accurate but still have some error.
        """
        dx = target[0] - current[0]
        dy = target[1] - current[1]
        distance = current_error
        
        # Corrections are more accurate (gain closer to 1.0)
        gain = random.gauss(0.92, 0.05)
        gain = np.clip(gain, 0.8, 1.05)
        
        # Less lateral error in corrections
        lateral_error = random.gauss(0, distance * 0.02)
        
        if distance > 0:
            perp_x = -dy / distance
            perp_y = dx / distance
        else:
            perp_x, perp_y = 0, 0
        
        endpoint_x = current[0] + dx * gain + perp_x * lateral_error
        endpoint_y = current[1] + dy * gain + perp_y * lateral_error
        
        error = math.sqrt(
            (target[0] - endpoint_x)**2 + (target[1] - endpoint_y)**2
        )
        
        return (endpoint_x, endpoint_y), error


# =============================================================================
# PATH GEOMETRY AND TORTUOSITY
# =============================================================================

class PathGeometry:
    """
    Generate realistic path curvature and deviation.
    
    Human paths are not straight lines - they have:
    - Slight curvature (biomechanical arc)
    - Path deviation maximal at midpoint
    - Fractal dimension 1.2-1.4
    - Straightness index 0.80-0.95
    """
    
    def __init__(
        self,
        curvature_scale: float = 0.15,
        midpoint_deviation: float = 0.12
    ):
        """
        Args:
            curvature_scale: Overall curvature as fraction of distance
            midpoint_deviation: Max perpendicular deviation as fraction of distance
                               (research: humans have straightness index 0.80-0.95)
        """
        self.curvature_scale = curvature_scale
        self.midpoint_deviation = midpoint_deviation
    
    def generate_curved_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        n_points: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a curved path with realistic deviation.
        
        Uses perpendicular deviation that peaks at midpoint,
        creating a slight biomechanical arc.
        """
        distance = math.sqrt(
            (end[0] - start[0])**2 + (end[1] - start[1])**2
        )
        
        if distance < 5 or n_points < 3:
            return (
                np.linspace(start[0], end[0], n_points),
                np.linspace(start[1], end[1], n_points)
            )
        
        # Direction vector
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Perpendicular vector (for deviation)
        perp_x = -dy / distance
        perp_y = dx / distance
        
        # Generate deviation profile (peaks at midpoint)
        t = np.linspace(0, 1, n_points)
        
        # Bell-shaped deviation (4t(1-t) peaks at t=0.5 with max value 1)
        base_deviation = 4 * t * (1 - t)
        
        # Human paths deviate significantly - straightness index should be 0.80-0.95
        # Research shows paths are NOT straight lines, they have biomechanical arcs
        curvature_sign = random.choice([-1, 1])
        curvature_magnitude = abs(random.gauss(
            self.midpoint_deviation * distance,
            self.midpoint_deviation * distance * 0.5
        ))
        
        # Ensure minimum deviation for human-like paths (research: straightness 0.80-0.95)
        # Min 5% deviation ensures we don't look robotic
        curvature_magnitude = max(curvature_magnitude, distance * 0.05)
        curvature_magnitude = min(curvature_magnitude, distance * 0.25)
        
        deviation = base_deviation * curvature_sign * curvature_magnitude
        
        # Add micro-corrections for fractal complexity (research: FD 1.2-1.4)
        # These simulate the small corrective submovements during travel
        perturbation = np.random.randn(n_points) * distance * 0.008
        perturbation = np.convolve(perturbation, np.ones(3)/3, mode='same')
        deviation += perturbation
        
        # Generate path
        x = start[0] + t * dx + deviation * perp_x
        y = start[1] + t * dy + deviation * perp_y
        
        return x, y
    
    def straightness_index(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> float:
        """
        Calculate straightness index (straight-line / actual path length).
        
        Human range: 0.80-0.95
        Robot (perfect): 1.0
        """
        # Straight-line distance
        straight = math.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2)
        
        # Actual path length
        dx = np.diff(x)
        dy = np.diff(y)
        path_length = np.sum(np.sqrt(dx**2 + dy**2))
        
        if path_length == 0:
            return 1.0
        
        return straight / path_length
    
    def path_rmse(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> float:
        """
        Calculate RMSE deviation from straight line.
        
        Human range: 10-25 pixels
        """
        if len(x) < 2:
            return 0.0
        
        # Line from start to end
        t = np.linspace(0, 1, len(x))
        line_x = x[0] + t * (x[-1] - x[0])
        line_y = y[0] + t * (y[-1] - y[0])
        
        # RMSE
        deviations = np.sqrt((x - line_x)**2 + (y - line_y)**2)
        return float(np.sqrt(np.mean(deviations**2)))


# =============================================================================
# CLICK AND TIMING MODELS
# =============================================================================

@dataclass
class ClickTimingParams:
    """
    Parameters for realistic click timing.
    
    Based on research:
    - Click duration: Log-normal, mean 85-130ms, std 20-30ms
    - Verification dwell: 200-500ms before click
    - Double-click interval: 100-500ms (OS limit)
    """
    # Click duration (mousedown to mouseup)
    click_duration_mu: float = 4.6  # log(100ms) ≈ 4.6
    click_duration_sigma: float = 0.25
    click_duration_min: float = MIN_CLICK_DURATION  # Physical floor
    click_duration_max: float = MAX_CLICK_DURATION  # Before long-press
    
    # Verification dwell before click
    verification_dwell_mu: float = 5.5  # log(250ms) ≈ 5.5
    verification_dwell_sigma: float = 0.3
    
    # Double-click interval
    double_click_mean: float = 0.230  # 230ms
    double_click_std: float = 0.080
    double_click_min: float = 0.100
    double_click_max: float = 0.450
    
    # Spatial drift during double-click (pixels)
    double_click_drift: float = 2.0


class ClickModel:
    """
    Human-like click timing generator.
    """
    
    def __init__(self, params: Optional[ClickTimingParams] = None):
        self.params = params or ClickTimingParams()
    
    def click_duration(self) -> float:
        """
        Generate click duration from log-normal distribution.
        
        Returns:
            Duration in seconds
        """
        duration = Distributions.log_normal(
            self.params.click_duration_mu,
            self.params.click_duration_sigma
        ) / 1000  # Convert from ms to seconds
        
        return np.clip(
            duration,
            self.params.click_duration_min,
            self.params.click_duration_max
        )
    
    def verification_dwell(self) -> float:
        """
        Generate pre-click verification dwell time.
        
        Returns:
            Dwell time in seconds
        """
        dwell = Distributions.log_normal(
            self.params.verification_dwell_mu,
            self.params.verification_dwell_sigma
        ) / 1000
        
        return np.clip(dwell, 0.10, 0.80)
    
    def double_click_interval(self) -> float:
        """
        Generate interval between clicks for double-click.
        
        Returns:
            Interval in seconds
        """
        interval = Distributions.truncated_normal(
            self.params.double_click_mean,
            self.params.double_click_std,
            self.params.double_click_min,
            self.params.double_click_max
        )
        return interval
    
    def double_click_drift(self) -> Tuple[float, float]:
        """
        Generate small position drift between double-click events.
        
        Humans typically drift 1-5 pixels between clicks.
        """
        drift_x = random.gauss(0, self.params.double_click_drift)
        drift_y = random.gauss(0, self.params.double_click_drift)
        return drift_x, drift_y


@dataclass
class ReactionTimeParams:
    """
    Reaction time parameters (Ex-Gaussian distribution).
    
    Average RT for visual stimulus: ~230ms
    Slows with age: +2-6ms per decade
    """
    # Gaussian component
    mu: float = 0.180  # 180ms
    sigma: float = 0.030  # 30ms
    
    # Exponential tail
    tau: float = 0.050  # 50ms
    
    # Age adjustment (ms per decade over 20)
    age_factor: float = 4.0
    user_age: int = 30


class ReactionTimeModel:
    """Generate human-like reaction times."""
    
    def __init__(self, params: Optional[ReactionTimeParams] = None):
        self.params = params or ReactionTimeParams()
    
    def sample(self) -> float:
        """
        Generate a reaction time sample.
        
        Returns:
            Reaction time in seconds
        """
        # Age adjustment
        decades_over_20 = max(0, (self.params.user_age - 20) / 10)
        age_adjustment = decades_over_20 * self.params.age_factor / 1000
        
        rt = Distributions.ex_gaussian(
            self.params.mu + age_adjustment,
            self.params.sigma,
            self.params.tau
        )
        
        return max(MIN_REACTION_TIME, rt)


# =============================================================================
# KEYBOARD INPUT MODEL
# =============================================================================

@dataclass
class KeyboardTimingParams:
    """
    Keyboard timing parameters.
    
    Inter-key interval varies by:
    - Key position (adjacent keys faster)
    - Word boundaries (pauses)
    - Cognitive load (thinking pauses)
    """
    # Base inter-key interval
    base_interval_mu: float = 0.100  # 100ms
    base_interval_sigma: float = 0.030
    
    # Key hold duration
    hold_duration_mu: float = 0.080  # 80ms
    hold_duration_sigma: float = 0.020
    hold_min: float = 0.040
    hold_max: float = 0.150
    
    # Word boundary pause
    word_pause_probability: float = 0.3
    word_pause_mu: float = 0.200
    word_pause_sigma: float = 0.100
    
    # Thinking pause
    think_probability: float = 0.03
    think_pause_mu: float = 0.500
    think_pause_sigma: float = 0.200
    
    # Typo probability
    typo_rate: float = 0.02
    
    # Correction delay (noticing + backspace)
    correction_notice_delay: float = 0.200
    correction_keystroke_delay: float = 0.080


class KeyboardModel:
    """Human-like keyboard input timing."""
    
    # Adjacent keys for typo generation
    ADJACENT_KEYS = {
        'a': ['q', 'w', 's', 'z'],
        'b': ['v', 'g', 'h', 'n'],
        'c': ['x', 'd', 'f', 'v'],
        'd': ['s', 'e', 'r', 'f', 'c', 'x'],
        'e': ['w', 's', 'd', 'r'],
        'f': ['d', 'r', 't', 'g', 'v', 'c'],
        'g': ['f', 't', 'y', 'h', 'b', 'v'],
        'h': ['g', 'y', 'u', 'j', 'n', 'b'],
        'i': ['u', 'j', 'k', 'o'],
        'j': ['h', 'u', 'i', 'k', 'm', 'n'],
        'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p'],
        'm': ['n', 'j', 'k'],
        'n': ['b', 'h', 'j', 'm'],
        'o': ['i', 'k', 'l', 'p'],
        'p': ['o', 'l'],
        'q': ['w', 'a'],
        'r': ['e', 'd', 'f', 't'],
        's': ['a', 'w', 'e', 'd', 'x', 'z'],
        't': ['r', 'f', 'g', 'y'],
        'u': ['y', 'h', 'j', 'i'],
        'v': ['c', 'f', 'g', 'b'],
        'w': ['q', 'a', 's', 'e'],
        'x': ['z', 's', 'd', 'c'],
        'y': ['t', 'g', 'h', 'u'],
        'z': ['a', 's', 'x'],
    }
    
    def __init__(self, params: Optional[KeyboardTimingParams] = None):
        self.params = params or KeyboardTimingParams()
    
    def inter_key_interval(self, prev_char: str, next_char: str) -> float:
        """
        Generate interval between keystrokes.
        
        Faster for adjacent keys, slower at word boundaries.
        """
        base = random.gauss(
            self.params.base_interval_mu,
            self.params.base_interval_sigma
        )
        
        # Word boundary pause
        if prev_char == ' ' or next_char == ' ':
            if random.random() < self.params.word_pause_probability:
                base += random.gauss(
                    self.params.word_pause_mu,
                    self.params.word_pause_sigma
                )
        
        # Random thinking pause
        if random.random() < self.params.think_probability:
            base += random.gauss(
                self.params.think_pause_mu,
                self.params.think_pause_sigma
            )
        
        return max(MIN_INTER_KEY_INTERVAL, base)
    
    def key_hold_duration(self) -> float:
        """Generate key hold duration."""
        hold = random.gauss(
            self.params.hold_duration_mu,
            self.params.hold_duration_sigma
        )
        return np.clip(hold, self.params.hold_min, self.params.hold_max)
    
    def should_typo(self) -> bool:
        """Check if we should generate a typo."""
        return random.random() < self.params.typo_rate
    
    def generate_typo(self, intended_char: str) -> Optional[str]:
        """Generate a typo for the given character."""
        char_lower = intended_char.lower()
        if char_lower in self.ADJACENT_KEYS:
            typo = random.choice(self.ADJACENT_KEYS[char_lower])
            if intended_char.isupper():
                typo = typo.upper()
            return typo
        return None


# =============================================================================
# MAIN NEUROMOTOR MOUSE CLASS
# =============================================================================

@dataclass
class NeuromotorConfig:
    """
    Complete configuration for neuromotor simulation.
    """
    # Fitts' Law parameters
    fitts: FittsParams = field(default_factory=FittsParams)
    
    # Velocity profile asymmetry (0.38-0.45 for humans)
    velocity_asymmetry: float = 0.42
    
    # Noise parameters (research-based defaults)
    # - noise_coefficient: ~2% of velocity is realistic
    # - tremor_amplitude: 0.1-0.2 pixels RMS is typical human tremor
    noise_coefficient: float = 0.02
    tremor_frequency: float = 10.0
    tremor_amplitude: float = 0.15
    
    # Path geometry (research: straightness index 0.80-0.95, not 1.0)
    path_curvature: float = 0.15
    path_deviation: float = 0.12
    
    # Submovement model
    primary_coverage: float = 0.95
    primary_error_std: float = 0.08
    max_corrections: int = 3
    
    # Click timing
    click_params: ClickTimingParams = field(default_factory=ClickTimingParams)
    
    # Sample rate (Hz)
    sample_rate: float = 60.0
    
    # Debug mode (slower, more visible)
    debug_mode: bool = False
    
    # Automatic post-action delays
    # NOTE: Neuromotor research focuses on PRE-action delays (verification dwell,
    # reaction time), which are already built into the library. Post-action delays
    # are less well-studied but represent cognitive processing between actions.
    # Set auto_delays=False to disable entirely for manual control.
    auto_delays: bool = True
    
    # Post-click: Minimal visual feedback acknowledgment
    # Research basis: Visual feedback latency ~50-100ms, but context-dependent
    # (clicking a button vs link vs checkbox have different cognitive requirements)
    # User should add explicit delays for page loads/animations
    post_click_delay: Tuple[float, float] = (0.05, 0.12)  # (min, max) seconds
    
    # Post-type: Brief pause after typing (cursor repositioning, eye movement)
    # Research basis: Limited - inferred from inter-keystroke intervals
    # User should add explicit delays before form submission
    post_type_delay: Tuple[float, float] = (0.05, 0.12)
    
    # Post-scroll: Reorientation + visual search for next target
    # Research basis: Visual search time 200-500ms (well-documented in HCI)
    # Saccade planning ~200ms, target acquisition ~200-400ms
    # This is the most justified automatic delay
    post_scroll_delay: Tuple[float, float] = (0.15, 0.4)


class NeuromotorMouse:
    """
    Research-grounded human mouse movement simulation.
    
    Implements:
    - Fitts' Law movement timing
    - Minimum Jerk trajectory with asymmetric velocity
    - Two-component submovement model
    - Signal-dependent noise with physiological tremor
    - Realistic path curvature
    - Log-normal click timing
    
    Usage:
        mouse = NeuromotorMouse()
        await mouse.move_to(500, 300, target_width=50, click=True)
    """
    
    def __init__(self, config: Optional[NeuromotorConfig] = None):
        self.config = config or NeuromotorConfig()
        
        # Initialize component models
        self.fitts = FittsLaw(self.config.fitts)
        self.trajectory = MinimumJerkTrajectory(self.config.velocity_asymmetry)
        self.noise = NeuromotorNoise(
            noise_coefficient=self.config.noise_coefficient,
            tremor_frequency=self.config.tremor_frequency,
            tremor_amplitude=self.config.tremor_amplitude,
            sample_rate=self.config.sample_rate
        )
        self.submovement = TwoComponentModel(
            primary_coverage=self.config.primary_coverage,
            primary_error_std=self.config.primary_error_std,
            max_corrections=self.config.max_corrections
        )
        self.path_geometry = PathGeometry(
            curvature_scale=self.config.path_curvature,
            midpoint_deviation=self.config.path_deviation
        )
        self.click_model = ClickModel(self.config.click_params)
        
        self._last_position = pyautogui.position()
    
    def _calculate_endpoint(
        self,
        target_center: Tuple[int, int],
        target_width: float,
        target_height: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        Calculate click endpoint using effective width distribution.
        
        Samples from bivariate normal centered on target,
        with σ derived from effective width for ~4% miss rate.
        """
        if target_height is None:
            target_height = target_width
        
        # Effective width -> standard deviation
        sigma_x = self.fitts.effective_width(target_width)
        sigma_y = self.fitts.effective_width(target_height)
        
        # Sample endpoint
        endpoint = Distributions.bivariate_normal(
            center=target_center,
            sigma_x=sigma_x,
            sigma_y=sigma_y,
            correlation=random.uniform(-0.1, 0.1)  # Small correlation
        )
        
        return endpoint
    
    async def move_to(
        self,
        x: int,
        y: int,
        target_width: float = 50.0,
        target_height: Optional[float] = None,
        click: bool = False,
        button: ButtonType = 'left'
    ) -> None:
        """
        Move to target with human-like kinematics.
        
        Args:
            x, y: Target center coordinates
            target_width: Width of clickable target (pixels)
            target_height: Height of target (defaults to width)
            click: Whether to click after moving
            button: Mouse button ('left', 'right', 'middle')
        """
        if target_height is None:
            target_height = target_width
        
        start = pyautogui.position()
        
        # Calculate where we'll actually aim (with endpoint distribution)
        endpoint = self._calculate_endpoint(
            (x, y), target_width, target_height
        )
        
        # Calculate distance for Fitts' Law
        distance = math.sqrt(
            (endpoint[0] - start[0])**2 + (endpoint[1] - start[1])**2
        )
        
        if distance < MIN_MOVEMENT_DISTANCE:
            # Too close to move meaningfully
            if click:
                await self._execute_click(button)
            return
        
        # Calculate total movement time via Fitts' Law
        total_duration = self.fitts.movement_time(
            distance, min(target_width, target_height)
        )
        
        # Debug mode: slow everything down
        if self.config.debug_mode:
            total_duration *= 3
        
        # Plan submovements
        submovements = self.submovement.plan_submovements(
            (float(start[0]), float(start[1])),
            endpoint,
            target_width
        )
        
        # Execute each submovement
        current_pos = (float(start[0]), float(start[1]))
        for sub_endpoint, time_fraction in submovements:
            sub_duration = total_duration * time_fraction
            await self._execute_submovement(
                current_pos, sub_endpoint, sub_duration
            )
            current_pos = sub_endpoint
        
        self._last_position = (int(endpoint[0]), int(endpoint[1]))
        
        if click:
            await self._execute_click(button)
    
    async def _execute_submovement(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        duration: float
    ) -> None:
        """Execute a single submovement with full kinematics."""
        
        n_samples = max(5, int(duration * self.config.sample_rate))
        
        # Generate base curved path
        base_x, base_y = self.path_geometry.generate_curved_path(
            start, end, n_samples
        )
        
        # Generate velocity profile for noise scaling
        times, positions, velocities = self.trajectory.generate_profile(
            duration, self.config.sample_rate
        )
        
        # Interpolate velocities to match path samples
        if len(velocities) != n_samples:
            velocities = np.interp(
                np.linspace(0, 1, n_samples),
                np.linspace(0, 1, len(velocities)),
                velocities
            )
        
        # Scale velocities by distance
        distance = math.sqrt(
            (end[0] - start[0])**2 + (end[1] - start[1])**2
        )
        velocities = velocities * distance
        
        # Apply neuromotor noise
        noisy_x, noisy_y = self.noise.add_noise_to_trajectory(
            base_x, base_y, velocities
        )
        
        # Calculate time delays based on velocity profile
        # Slower at start/end, faster in middle
        time_weights = velocities / (np.sum(velocities) + 1e-6)
        time_weights = 1.0 / (time_weights + 0.1)  # Invert: slow = more time
        time_weights = time_weights / np.sum(time_weights)
        time_delays = time_weights * duration
        
        # Execute movement
        for i in range(n_samples):
            pyautogui.moveTo(int(noisy_x[i]), int(noisy_y[i]))
            if i < len(time_delays):
                await asyncio.sleep(time_delays[i])
    
    async def _execute_click(self, button: ButtonType = 'left') -> None:
        """Execute click with human-like timing."""
        
        # Verification dwell
        dwell = self.click_model.verification_dwell()
        await asyncio.sleep(dwell)
        
        # Click with proper duration
        duration = self.click_model.click_duration()
        pyautogui.mouseDown(button=button)
        await asyncio.sleep(duration)
        pyautogui.mouseUp(button=button)
        
        # Post-click processing delay (automatic)
        if self.config.auto_delays:
            delay = random.uniform(*self.config.post_click_delay)
            await asyncio.sleep(delay)
    
    async def click(
        self,
        button: ButtonType = 'left',
        clicks: int = 1
    ) -> None:
        """
        Click at current position.
        
        Args:
            button: Mouse button
            clicks: Number of clicks (1 for single, 2 for double)
        """
        for i in range(clicks):
            await self._execute_click(button)
            
            if i < clicks - 1:
                # Inter-click delay for multi-click
                interval = self.click_model.double_click_interval()
                await asyncio.sleep(interval)
                
                # Small drift between clicks
                drift_x, drift_y = self.click_model.double_click_drift()
                current = pyautogui.position()
                pyautogui.moveTo(
                    int(current[0] + drift_x),
                    int(current[1] + drift_y)
                )
    
    async def scroll(
        self,
        clicks: int,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> None:
        """
        Human-like scrolling.
        
        Args:
            clicks: Scroll amount (positive=up, negative=down)
            x, y: Optional position to scroll at
        """
        if x is not None and y is not None:
            await self.move_to(x, y)
        
        # Break into chunks with variable timing
        direction = 1 if clicks > 0 else -1
        remaining = abs(clicks)
        
        while remaining > 0:
            # Variable chunk size
            chunk = min(remaining, random.randint(1, 3))
            pyautogui.scroll(chunk * direction)
            remaining -= chunk
            
            # Variable delay between scroll events
            await asyncio.sleep(random.uniform(0.03, 0.15))
        
        # Post-scroll processing delay (automatic)
        if self.config.auto_delays:
            delay = random.uniform(*self.config.post_scroll_delay)
            await asyncio.sleep(delay)
    
    async def hover(
        self,
        x: int,
        y: int,
        target_width: float = 50.0,
        target_height: Optional[float] = None
    ) -> None:
        """
        Move to target without clicking (hover).
        
        Args:
            x, y: Target coordinates
            target_width: Width of target area (for Fitts' Law timing)
            target_height: Height of target (defaults to width)
        """
        await self.move_to(x, y, target_width, target_height, click=False)
    
    async def double_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        target_width: float = 50.0
    ) -> None:
        """
        Double-click at position (or current position if not specified).
        
        Args:
            x, y: Optional target coordinates
            target_width: Width of target for movement timing
        """
        if x is not None and y is not None:
            await self.move_to(x, y, target_width=target_width, click=False)
        await self.click(clicks=2)
    
    async def right_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        target_width: float = 50.0
    ) -> None:
        """
        Right-click at position (or current position if not specified).
        
        Args:
            x, y: Optional target coordinates
            target_width: Width of target for movement timing
        """
        if x is not None and y is not None:
            await self.move_to(x, y, target_width=target_width, click=False)
        await self.click(button='right')
    
    async def triple_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        target_width: float = 50.0
    ) -> None:
        """
        Triple-click at position (select paragraph/line).
        
        Args:
            x, y: Optional target coordinates
            target_width: Width of target for movement timing
        """
        if x is not None and y is not None:
            await self.move_to(x, y, target_width=target_width, click=False)
        await self.click(clicks=3)
    
    async def move_relative(
        self,
        dx: int,
        dy: int,
        target_width: float = 50.0
    ) -> None:
        """
        Move cursor by relative offset from current position.
        
        Args:
            dx, dy: Relative movement in pixels
            target_width: Assumed target width for timing
        """
        current = pyautogui.position()
        await self.move_to(
            int(current[0] + dx),
            int(current[1] + dy),
            target_width=target_width,
            click=False
        )
    
    async def drag_to(
        self,
        x: int,
        y: int,
        target_width: float = 50.0,
        target_height: Optional[float] = None,
        button: ButtonType = 'left'
    ) -> None:
        """
        Drag from current position to target with human-like movement.
        
        Holds mouse button down, moves with natural kinematics,
        then releases at destination.
        
        Args:
            x, y: Target coordinates
            target_width: Width of drop target
            target_height: Height of drop target (defaults to width)
            button: Mouse button to hold during drag
        """
        if target_height is None:
            target_height = target_width
        
        # Small pause before starting drag
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Press and hold
        pyautogui.mouseDown(button=button)
        await asyncio.sleep(random.uniform(0.02, 0.08))
        
        # Move to target (drag movements are typically slower/more careful)
        start = pyautogui.position()
        endpoint = self._calculate_endpoint((x, y), target_width, target_height)
        
        distance = math.sqrt(
            (endpoint[0] - start[0])**2 + (endpoint[1] - start[1])**2
        )
        
        if distance > MIN_MOVEMENT_DISTANCE:
            # Drag movements take longer (more careful)
            total_duration = self.fitts.movement_time(
                distance, min(target_width, target_height)
            ) * 1.3  # 30% slower for drags
            
            # Single smooth movement for drag (no submovements)
            await self._execute_submovement(
                (float(start[0]), float(start[1])),
                endpoint,
                total_duration
            )
        
        # Small pause before release
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Release
        pyautogui.mouseUp(button=button)
        self._last_position = (int(endpoint[0]), int(endpoint[1]))


class NeuromotorKeyboard:
    """
    Human-like keyboard input with realistic timing.
    """
    
    def __init__(
        self, 
        config: Optional[KeyboardTimingParams] = None,
        auto_delays: bool = True,
        post_type_delay: Tuple[float, float] = (0.2, 0.5)
    ):
        self.model = KeyboardModel(config)
        self._last_char = ''
        self.auto_delays = auto_delays
        self.post_type_delay = post_type_delay
    
    async def type_text(
        self,
        text: str,
        with_typos: bool = True
    ) -> None:
        """
        Type text with human-like timing and optional typos.
        
        Args:
            text: Text to type
            with_typos: Whether to simulate occasional typos
        """
        i = 0
        while i < len(text):
            char = text[i]
            
            # Check for typo
            if with_typos and self.model.should_typo():
                typo = self.model.generate_typo(char)
                if typo:
                    # Type the typo
                    await self._press_key(typo)
                    
                    # Notice the mistake
                    await asyncio.sleep(
                        self.model.params.correction_notice_delay +
                        random.uniform(0, 0.1)
                    )
                    
                    # Backspace
                    await self._press_key('backspace')
                    await asyncio.sleep(
                        self.model.params.correction_keystroke_delay
                    )
            
            # Type the actual character
            await self._press_key(char)
            
            # Inter-key delay
            next_char = text[i + 1] if i + 1 < len(text) else ''
            delay = self.model.inter_key_interval(char, next_char)
            await asyncio.sleep(delay)
            
            self._last_char = char
            i += 1
        
        # Post-typing processing delay (automatic)
        if self.auto_delays:
            delay = random.uniform(*self.post_type_delay)
            await asyncio.sleep(delay)
    
    async def _press_key(self, key: str) -> None:
        """Press a key with realistic hold duration."""
        hold = self.model.key_hold_duration()
        pyautogui.keyDown(key)
        await asyncio.sleep(hold)
        pyautogui.keyUp(key)
    
    async def press_key(self, key: str) -> None:
        """Public method to press a single key."""
        await self._press_key(key)
    
    async def hotkey(self, *keys: str) -> None:
        """
        Press a key combination (e.g., Ctrl+C).
        """
        # Press all keys down with slight delays
        for key in keys:
            pyautogui.keyDown(key)
            await asyncio.sleep(random.uniform(0.02, 0.05))
        
        # Hold
        await asyncio.sleep(random.uniform(0.05, 0.10))
        
        # Release in reverse order
        for key in reversed(keys):
            pyautogui.keyUp(key)
            await asyncio.sleep(random.uniform(0.02, 0.05))


# =============================================================================
# COMBINED INPUT CONTROLLER
# =============================================================================

class NeuromotorInput:
    """
    Complete human-like input controller.
    
    Usage:
        human = NeuromotorInput()
        await human.mouse.move_to(500, 300, target_width=100, click=True)
        await human.keyboard.type_text("Hello, world!")
    """
    
    def __init__(
        self,
        mouse_config: Optional[NeuromotorConfig] = None,
        keyboard_config: Optional[KeyboardTimingParams] = None
    ):
        self.config = mouse_config or NeuromotorConfig()
        self.mouse = NeuromotorMouse(self.config)
        self.keyboard = NeuromotorKeyboard(
            keyboard_config,
            auto_delays=self.config.auto_delays,
            post_type_delay=self.config.post_type_delay
        )
        self.reaction = ReactionTimeModel()
    
    async def click_element(
        self,
        element_bounds: Tuple[int, int, int, int],
        button: ButtonType = 'left'
    ) -> None:
        """
        Click within an element's bounds with realistic targeting.
        
        Args:
            element_bounds: (x, y, width, height) of the element
            button: Mouse button to click
        """
        x, y, width, height = element_bounds
        
        # Calculate center
        center_x = x + width // 2
        center_y = y + height // 2
        
        await self.mouse.move_to(
            center_x, center_y,
            target_width=width,
            target_height=height,
            click=True,
            button=button
        )
    
    async def _get_nodriver_screen_coords(
        self,
        element: Any,
        page: Any,
        chrome_height: Optional[int] = None
    ) -> Tuple[int, int, int, int]:
        """
        Convert nodriver element to screen coordinates.
        
        Args:
            element: nodriver Element object
            page: nodriver Page object
            chrome_height: Browser chrome/toolbar height in pixels. If None (default),
                          auto-detects using JavaScript to measure window.outerHeight - window.innerHeight.
                          Falls back to 0 for headless/container environments.
        
        Returns:
            (x, y, width, height) where x,y is the top-left corner in screen coordinates
        """
        # Get window bounds - nodriver returns (WindowID, Bounds) tuple
        _, bounds = await page.get_window()
        
        # Auto-detect chrome height if not provided
        if chrome_height is None:
            try:
                # Use JavaScript to get accurate chrome height
                # This works across different browsers and OS configurations
                result = await page.evaluate("window.outerHeight - window.innerHeight")
                chrome_height = int(result) if result else 0
            except Exception:
                # Fallback for headless/container environments where chrome may not exist
                chrome_height = 0
        
        # Use getBoundingClientRect() to get viewport-relative coordinates
        # This accounts for scroll position automatically
        try:
            rect = await page.evaluate("""
                (element) => {
                    const rect = element.getBoundingClientRect();
                    return {
                        x: rect.left,
                        y: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                }
            """, element)
            
            # Convert viewport coordinates to screen coordinates
            screen_x = int(bounds.left + rect['x'])
            screen_y = int(bounds.top + chrome_height + rect['y'])
            
            return screen_x, screen_y, int(rect['width']), int(rect['height'])
            
        except Exception:
            # Fallback to element.get_position() if JavaScript fails
            # Note: This may not account for scroll position correctly
            box = await element.get_position()
            screen_x = int(bounds.left + box.x)
            screen_y = int(bounds.top + chrome_height + box.y)
            return screen_x, screen_y, int(box.width), int(box.height)
    
    async def click_nodriver_element(
        self,
        element: Any,
        page: Any,
        button: ButtonType = 'left',
        chrome_height: Optional[int] = None,
        use_cdp_click: bool = False,
        scroll_into_view: bool = True
    ) -> None:
        """
        Click a nodriver element with human-like movement.
        
        Automatically converts element position to screen coordinates and optionally
        scrolls the element into view if it's not visible.
        
        Args:
            element: nodriver Element object
            page: nodriver Page object (for window position)
            button: Mouse button to click
            chrome_height: Browser chrome height in pixels. If None (default),
                          auto-detects using JavaScript. Set to 0 for headless.
            use_cdp_click: If True, uses CDP (Chrome DevTools Protocol) click for
                          maximum reliability instead of pyautogui coordinate-based click.
                          The mouse still moves naturally for visual effect.
            scroll_into_view: If True (default), automatically scrolls element into
                            view if it's not visible in the viewport.
        
        Example:
            button = await page.select('button.submit')
            await human.click_nodriver_element(button, page)
            
            # For maximum reliability in complex scenarios:
            await human.click_nodriver_element(button, page, use_cdp_click=True)
        """
        # Scroll element into view if needed
        if scroll_into_view:
            try:
                await page.evaluate("""
                    (element) => {
                        element.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center',
                            inline: 'center'
                        });
                    }
                """, element)
                # Wait for smooth scroll animation to complete
                # Smooth scrolls can take 500-1000ms depending on distance
                await asyncio.sleep(random.uniform(0.6, 1.0))
            except Exception:
                pass  # Continue even if scroll fails
        
        x, y, width, height = await self._get_nodriver_screen_coords(
            element, page, chrome_height
        )
        
        # Calculate center of element (coords are top-left)
        center_x = x + width // 2
        center_y = y + height // 2
        
        # Move mouse naturally for visual effect
        await self.mouse.move_to(
            center_x, center_y,
            target_width=width,
            target_height=height,
            click=not use_cdp_click,  # Only click via pyautogui if not using CDP
            button=button
        )
        
        # Use CDP click for reliability if requested
        if use_cdp_click:
            await element.click()
    
    async def fill_nodriver_input(
        self,
        element: Any,
        page: Any,
        text: str,
        clear_first: bool = True,
        chrome_height: Optional[int] = None,
        with_typos: bool = True,
        scroll_into_view: bool = True
    ) -> None:
        """
        Click a nodriver input element and type text.
        
        Args:
            element: nodriver Element object (input/textarea)
            page: nodriver Page object
            text: Text to type
            clear_first: Whether to clear existing text first (uses triple-click
                        to select all text in the specific element, not globally)
            chrome_height: Browser chrome height in pixels. If None (default),
                          auto-detects using JavaScript.
            with_typos: Whether to simulate occasional typos
            scroll_into_view: If True (default), automatically scrolls element into
                            view if it's not visible in the viewport.
        
        Example:
            search_box = await page.select('input[name="q"]')
            await human.fill_nodriver_input(search_box, page, "search query")
        """
        # Click to focus (with auto-scroll)
        await self.click_nodriver_element(
            element, page, 
            chrome_height=chrome_height,
            scroll_into_view=scroll_into_view
        )
        
        # Reaction time before typing
        await asyncio.sleep(self.reaction.sample())
        
        if clear_first:
            # Use triple-click to select all text in THIS element (not global Cmd+A)
            # This is more targeted and won't accidentally select other content
            await asyncio.sleep(random.uniform(0.05, 0.1))
            
            # Triple-click with realistic timing
            await self.mouse.click()
            await asyncio.sleep(random.uniform(0.08, 0.15))
            await self.mouse.click()
            await asyncio.sleep(random.uniform(0.08, 0.15))
            await self.mouse.click()  # Triple-click = select all in input
            
            await asyncio.sleep(random.uniform(0.1, 0.2))
            
            # Type will replace selected text, or backspace if needed
            await self.keyboard.press_key('backspace')
            await asyncio.sleep(random.uniform(0.1, 0.2))
        
        await self.keyboard.type_text(text, with_typos=with_typos)
    
    async def fill_input(
        self,
        element_bounds: Tuple[int, int, int, int],
        text: str,
        clear_first: bool = True
    ) -> None:
        """
        Click an input field and type text.
        
        Args:
            element_bounds: (x, y, width, height) of the input element
            text: Text to type
            clear_first: Whether to clear existing text first
        """
        # Click to focus
        await self.click_element(element_bounds)
        
        # Reaction time before starting to type
        await asyncio.sleep(self.reaction.sample())
        
        if clear_first:
            # Select all (use Cmd on macOS, Ctrl elsewhere)
            await self.keyboard.hotkey(MODIFIER_KEY, 'a')
            await asyncio.sleep(random.uniform(0.1, 0.2))
            await self.keyboard.press_key('backspace')
            await asyncio.sleep(random.uniform(0.1, 0.2))
        
        # Type the text
        await self.keyboard.type_text(text)
    
    async def wait_human(
        self,
        min_seconds: float = 0.5,
        max_seconds: float = 2.0
    ) -> None:
        """
        Add a human-like pause (e.g., reading, thinking, general delay).
        
        Use this for context-specific delays like:
        - Reading content before next action
        - Pausing to think/decide
        - General human-like pauses
        
        Note: For page loads, use wait_for_page() instead.
        
        Args:
            min_seconds: Minimum wait time
            max_seconds: Maximum wait time
        
        Example:
            await human.mouse.click()
            await human.wait_human(0.5, 1.5)  # Brief pause to think
        """
        duration = Distributions.log_normal(
            math.log((min_seconds + max_seconds) / 2 * 1000),
            0.3
        ) / 1000
        duration = np.clip(duration, min_seconds, max_seconds * 1.5)
        await asyncio.sleep(duration)
    
    async def wait_for_page(
        self,
        page: Any,
        min_read_time: float = 0.3,
        max_read_time: float = 1.0,
        timeout: float = 10.0
    ) -> None:
        """
        Wait for page to fully load, then add human-like reading/orientation delay.
        
        This combines technical page load waiting with realistic human behavior:
        1. Waits for page to be ready (network idle, DOM loaded)
        2. Adds natural delay for reading/orienting to new content
        
        Args:
            page: nodriver Page object
            min_read_time: Minimum reading/orientation time after load (seconds)
            max_read_time: Maximum reading/orientation time after load (seconds)
            timeout: Maximum time to wait for page load (seconds)
        
        Example:
            await human.keyboard.press_key('enter')  # Submit form
            await human.wait_for_page(page)  # Wait for navigation + human delay
            
            # Or customize reading time:
            await human.click_nodriver_element(link, page)
            await human.wait_for_page(page, min_read_time=0.5, max_read_time=2.0)
        """
        try:
            # Wait for page to be in a loaded state
            # nodriver's page has methods to wait for various states
            # We'll use a combination of checks with timeout
            start_time = asyncio.get_event_loop().time()
            
            # Wait for the page to reach a stable state
            # Try to wait for network idle (most reliable for SPAs)
            try:
                await asyncio.wait_for(
                    page.wait(timeout / 1000),  # nodriver uses milliseconds
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Page didn't fully load within timeout, continue anyway
                pass
            except AttributeError:
                # If wait() doesn't exist or has different signature, use simpler approach
                # Wait for document.readyState to be complete
                try:
                    end_time = start_time + timeout
                    while asyncio.get_event_loop().time() < end_time:
                        ready_state = await page.evaluate("document.readyState")
                        if ready_state == "complete":
                            break
                        await asyncio.sleep(0.1)
                except Exception:
                    # Fallback: just wait a bit
                    await asyncio.sleep(0.5)
            
        except Exception:
            # If any page load detection fails, continue with just human delay
            pass
        
        # Add human reading/orientation delay
        # Research: Initial page scan ~300-1000ms, understanding content ~500-2000ms
        read_delay = Distributions.log_normal(
            math.log((min_read_time + max_read_time) / 2 * 1000),
            0.3
        ) / 1000
        read_delay = np.clip(read_delay, min_read_time, max_read_time * 1.5)
        await asyncio.sleep(read_delay)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def human_move_and_click(
    x: int,
    y: int,
    target_width: float = 50.0,
    button: ButtonType = 'left'
) -> None:
    """Quick function to move and click with human-like behavior."""
    mouse = NeuromotorMouse()
    await mouse.move_to(x, y, target_width=target_width, click=True, button=button)


async def human_type(text: str, with_typos: bool = False) -> None:
    """Quick function to type with human-like behavior."""
    keyboard = NeuromotorKeyboard()
    await keyboard.type_text(text, with_typos=with_typos)


# =============================================================================
# DIAGNOSTICS AND VALIDATION
# =============================================================================

class MovementDiagnostics:
    """
    Tools for validating that movements are human-plausible.
    
    Use for testing/debugging to ensure movements won't be detected.
    """
    
    def __init__(self):
        self.fitts = FittsLaw()
        self.path = PathGeometry()
    
    def analyze_trajectory(
        self,
        x: np.ndarray,
        y: np.ndarray,
        times: np.ndarray,
        target_width: float
    ) -> dict:
        """
        Analyze a recorded trajectory for human plausibility.
        
        Returns:
            Dictionary of metrics with pass/fail indicators
        """
        distance = math.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2)
        duration = times[-1] - times[0]
        
        # Fitts' Law validation
        is_valid_fitts, throughput = self.fitts.validate_human_plausible(
            distance, target_width, duration
        )
        
        # Path metrics
        straightness = self.path.straightness_index(x, y)
        rmse = self.path.path_rmse(x, y)
        
        # Velocity analysis
        dx = np.diff(x)
        dy = np.diff(y)
        dt = np.diff(times)
        velocities = np.sqrt(dx**2 + dy**2) / (dt + 1e-6)
        
        # Find peak velocity timing
        peak_idx = np.argmax(velocities)
        peak_time_fraction = peak_idx / len(velocities) if len(velocities) > 0 else 0.5
        
        return {
            'distance_px': distance,
            'duration_s': duration,
            'throughput_bps': throughput,
            'throughput_valid': is_valid_fitts,  # Should be True (<12 bps)
            'straightness_index': straightness,
            'straightness_valid': 0.75 <= straightness <= 0.98,
            'path_rmse_px': rmse,
            'rmse_valid': 5 <= rmse <= 40,
            'peak_velocity_px_s': np.max(velocities) if len(velocities) > 0 else 0,
            'peak_velocity_timing': peak_time_fraction,
            'velocity_asymmetry_valid': 0.30 <= peak_time_fraction <= 0.55,
            'overall_valid': (
                is_valid_fitts and
                0.75 <= straightness <= 0.98 and
                0.30 <= peak_time_fraction <= 0.55
            )
        }


if __name__ == "__main__":
    # Example usage and validation
    async def demo():
        print("Neuromotor Input Library Demo")
        print("=" * 50)
        
        # Create input controller
        config = NeuromotorConfig(debug_mode=True)  # Slow for visibility
        human = NeuromotorInput(mouse_config=config)
        
        # Demo movement
        print("\nMoving to (500, 300) with 100px target...")
        await human.mouse.move_to(500, 300, target_width=100, click=True)
        
        print("\nTyping 'Hello World'...")
        await human.keyboard.type_text("Hello World")
        
        print("\nDemo complete!")
    
    asyncio.run(demo())
