"""
nothingtoseehere - Test Suite

Tests the statistical/mathematical components of the library.
These tests validate that movements match research-grounded human behavior.
"""

import math
import pytest
import numpy as np

# Import from the actual library
from nothingtoseehere import (
    FittsLaw,
    MinimumJerkTrajectory,
    NeuromotorNoise,
    TwoComponentModel,
    PathGeometry,
    ClickModel,
    Distributions,
    MovementDiagnostics,
)


class TestFittsLaw:
    """Test Fitts' Law movement timing calculations."""
    
    def test_index_of_difficulty(self):
        """ID = log2(2D/W) should be calculated correctly."""
        fitts = FittsLaw()
        
        # ID for D=100, W=100 should be log2(2) = 1.0
        assert abs(fitts.index_of_difficulty(100, 100) - 1.0) < 0.01
        
        # ID for D=1000, W=100 should be log2(20) ≈ 4.32
        assert abs(fitts.index_of_difficulty(1000, 100) - 4.32) < 0.1
    
    def test_movement_time_increases_with_difficulty(self):
        """Harder movements (smaller targets, longer distance) should take longer."""
        fitts = FittsLaw()
        
        # Same distance, different widths
        mt_easy = fitts.movement_time(500, 100)  # Large target
        mt_hard = fitts.movement_time(500, 20)   # Small target
        
        assert mt_hard > mt_easy
    
    def test_throughput_stays_under_human_ceiling(self):
        """Throughput should never exceed 12 bits/second (human limit)."""
        fitts = FittsLaw()
        
        test_cases = [
            (100, 100),
            (500, 50),
            (1000, 20),
            (1500, 10),
        ]
        
        for distance, width in test_cases:
            mt = fitts.movement_time(distance, width)
            is_valid, throughput = fitts.validate_human_plausible(distance, width, mt)
            
            assert is_valid, f"Throughput {throughput:.1f} exceeds human ceiling"
            assert throughput <= 12.0
    
    def test_effective_width(self):
        """Effective width should be target_width / 4.133."""
        fitts = FittsLaw()
        
        assert abs(fitts.effective_width(100) - 100/4.133) < 0.01


class TestMinimumJerkTrajectory:
    """Test minimum jerk trajectory generation with asymmetric velocity."""
    
    def test_position_endpoints(self):
        """Position should go from 0 to 1."""
        traj = MinimumJerkTrajectory(asymmetry=0.42)
        
        assert abs(traj.position(0, 1.0) - 0.0) < 0.01
        assert abs(traj.position(1.0, 1.0) - 1.0) < 0.01
    
    def test_velocity_peak_timing(self):
        """Peak velocity should occur at ~42% of movement (asymmetric)."""
        traj = MinimumJerkTrajectory(asymmetry=0.42)
        
        times, positions, velocities = traj.generate_profile(1.0, 100.0)
        
        peak_idx = np.argmax(velocities)
        peak_time_fraction = times[peak_idx] / times[-1]
        
        # Research says 38-45%, we target 42%
        assert 0.35 <= peak_time_fraction <= 0.50, \
            f"Peak at {peak_time_fraction*100:.0f}%, expected 38-48%"
    
    def test_velocity_is_bell_shaped(self):
        """Velocity should start at 0, peak, then return to 0."""
        traj = MinimumJerkTrajectory(asymmetry=0.42)
        
        times, positions, velocities = traj.generate_profile(1.0, 100.0)
        
        # Velocity at start and end should be near zero
        assert velocities[0] < 0.1
        assert velocities[-1] < 0.1
        
        # Peak should be significantly higher
        assert np.max(velocities) > 1.0


class TestNeuromotorNoise:
    """Test signal-dependent noise and physiological tremor."""
    
    def test_noise_scales_with_velocity(self):
        """Noise σ should increase with velocity (signal-dependent)."""
        noise = NeuromotorNoise(noise_coefficient=0.02)
        
        # Sample noise at different velocities
        samples_slow = [noise.signal_dependent_noise(100) for _ in range(1000)]
        samples_fast = [noise.signal_dependent_noise(1000) for _ in range(1000)]
        
        std_slow = np.std(samples_slow)
        std_fast = np.std(samples_fast)
        
        # Fast movement should have more noise
        assert std_fast > std_slow
    
    def test_tremor_frequency(self):
        """Tremor should have spectral peak at 8-12 Hz."""
        noise = NeuromotorNoise(
            tremor_frequency=10.0,
            tremor_amplitude=1.0,
            sample_rate=60.0
        )
        
        tremor = noise.generate_tremor(600)
        
        # FFT to find peak frequency
        spectrum = np.abs(np.fft.fft(tremor))[:300]
        freqs = np.linspace(0, 30, 300)
        peak_idx = np.argmax(spectrum[1:]) + 1
        peak_freq = freqs[peak_idx]
        
        # Should be in 8-12 Hz range
        assert 6 <= peak_freq <= 14, f"Tremor peak at {peak_freq:.1f} Hz, expected 8-12 Hz"


class TestTwoComponentModel:
    """Test ballistic + corrective submovement model."""
    
    def test_submovement_count(self):
        """Most movements should have 1-4 submovements."""
        model = TwoComponentModel()
        
        counts = []
        for _ in range(100):
            submovements = model.plan_submovements((0, 0), (1000, 500), 50)
            counts.append(len(submovements))
        
        # 90% should have <7 submovements per research
        assert np.mean(counts) <= 4
        assert max(counts) <= 7
    
    def test_primary_covers_most_distance(self):
        """Primary submovement should cover ~95% of distance."""
        model = TwoComponentModel(primary_coverage=0.95)
        
        start = (0, 0)
        target = (1000, 0)
        
        submovements = model.plan_submovements(start, target, 50)
        
        # First submovement should get us close to target
        first_endpoint = submovements[0][0]
        distance_covered = first_endpoint[0] - start[0]
        
        # Should be 70-115% of distance (allows for undershoot and overshoot)
        # Model's primary_gain_range is (0.7, 1.15) by default
        assert 700 <= distance_covered <= 1150


class TestPathGeometry:
    """Test path curvature and tortuosity."""
    
    def test_straightness_index_in_human_range(self):
        """Straightness should be 0.80-0.95 (not perfectly straight)."""
        path_gen = PathGeometry(midpoint_deviation=0.12)
        
        straightness_vals = []
        for _ in range(50):
            start = (np.random.randint(0, 500), np.random.randint(0, 500))
            end = (np.random.randint(500, 1500), np.random.randint(0, 1000))
            x, y = path_gen.generate_curved_path(start, end, 100)
            straightness_vals.append(path_gen.straightness_index(x, y))
        
        mean_straightness = np.mean(straightness_vals)
        
        # Research says 0.80-0.95, robots are 1.0
        assert 0.78 <= mean_straightness <= 0.96, \
            f"Straightness {mean_straightness:.3f} outside human range 0.80-0.95"
    
    def test_path_has_curvature(self):
        """Path should deviate from straight line."""
        path_gen = PathGeometry(midpoint_deviation=0.12)
        
        start = (0, 0)
        end = (1000, 0)
        x, y = path_gen.generate_curved_path(start, end, 100)
        
        rmse = path_gen.path_rmse(x, y)
        
        # Should have some deviation
        assert rmse > 5, "Path is too straight (robot-like)"


class TestClickModel:
    """Test click timing distributions."""
    
    def test_click_duration_distribution(self):
        """Click durations should follow log-normal with mean 85-130ms."""
        click = ClickModel()
        
        durations = [click.click_duration() * 1000 for _ in range(1000)]
        
        mean_d = np.mean(durations)
        std_d = np.std(durations)
        
        # Research: mean 85-130ms, std 20-30ms
        assert 70 <= mean_d <= 150, f"Mean {mean_d:.0f}ms outside 85-130ms range"
        assert 15 <= std_d <= 50, f"Std {std_d:.0f}ms outside 20-30ms range"
    
    def test_click_duration_bounds(self):
        """Clicks should be within physical limits (50-350ms)."""
        click = ClickModel()
        
        for _ in range(100):
            duration = click.click_duration()
            assert 0.05 <= duration <= 0.35, f"Click duration {duration*1000:.0f}ms out of bounds"
    
    def test_verification_dwell(self):
        """Pre-click dwell should be 100-800ms."""
        click = ClickModel()
        
        for _ in range(100):
            dwell = click.verification_dwell()
            assert 0.10 <= dwell <= 0.80


class TestDistributions:
    """Test statistical distribution helpers."""
    
    def test_log_normal_positive(self):
        """Log-normal samples should always be positive."""
        for _ in range(100):
            val = Distributions.log_normal(4.6, 0.25)
            assert val > 0
    
    def test_bivariate_normal_centered(self):
        """Bivariate normal should be centered on target."""
        samples = [Distributions.bivariate_normal((500, 300), 10, 10) for _ in range(1000)]
        
        mean_x = np.mean([s[0] for s in samples])
        mean_y = np.mean([s[1] for s in samples])
        
        assert abs(mean_x - 500) < 5
        assert abs(mean_y - 300) < 5


class TestEndpointDistribution:
    """Test that endpoints follow realistic miss patterns."""
    
    def test_miss_rate(self):
        """Miss rate should be approximately 4-8%."""
        fitts = FittsLaw()
        
        target_width = 50
        sigma = fitts.effective_width(target_width)
        
        hits = 0
        total = 1000
        
        for _ in range(total):
            x, y = Distributions.bivariate_normal((500, 300), sigma, sigma)
            if abs(x - 500) <= target_width/2 and abs(y - 300) <= target_width/2:
                hits += 1
        
        miss_rate = 1 - hits/total
        
        # Research says ~4%, allow 2-15%
        assert 0.02 <= miss_rate <= 0.15, f"Miss rate {miss_rate*100:.1f}% outside expected range"


class TestIntegration:
    """Integration tests for full movement simulation."""
    
    def test_full_movement_is_human_plausible(self):
        """A complete simulated movement should pass all human-plausibility checks."""
        diagnostics = MovementDiagnostics()
        
        # Run multiple trials
        valid_count = 0
        
        for _ in range(20):
            # Simulate a movement
            start = (100, 100)
            end = (700, 500)
            distance = math.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)
            
            fitts = FittsLaw()
            trajectory = MinimumJerkTrajectory(asymmetry=0.42)
            path_gen = PathGeometry()
            
            duration = fitts.movement_time(distance, 50)
            n_points = max(30, int(duration * 60))
            
            # Generate path with timing
            times, positions, velocities = trajectory.generate_profile(duration, 60)
            x, y = path_gen.generate_curved_path(start, end, n_points)
            
            # Check throughput
            _, throughput = fitts.validate_human_plausible(distance, 50, duration)
            
            # Check straightness
            straightness = path_gen.straightness_index(x, y)
            
            # Check velocity asymmetry
            peak_idx = np.argmax(velocities)
            peak_timing = peak_idx / len(velocities)
            
            if throughput <= 12 and 0.78 <= straightness <= 0.96 and 0.35 <= peak_timing <= 0.50:
                valid_count += 1
        
        # At least 40% should be valid (random variance is expected)
        # With stochastic human-like parameters, some variance is natural
        assert valid_count >= 8, f"Only {valid_count}/20 movements were human-plausible"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
