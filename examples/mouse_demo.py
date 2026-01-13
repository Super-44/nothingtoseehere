#!/usr/bin/env python3
"""
Simple Mouse Movement Demo

Demonstrates the nothingtoseehere library by moving the mouse
around the screen with human-like kinematics.

No browser required - just watch your mouse cursor!

Run with: python examples/mouse_demo.py
"""

import asyncio
import random
import sys
import os

# Add parent directory to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nothingtoseehere import (
    NeuromotorInput,
    NeuromotorConfig,
    NeuromotorMouse,
    FittsParams,
    MovementDiagnostics,
)
import pyautogui


async def demo_basic_movement():
    """Show basic mouse movement patterns."""
    print("\n" + "=" * 60)
    print("🐭 Demo 1: Basic Mouse Movements")
    print("=" * 60)
    print("\nWatch your cursor move with human-like kinematics!")
    print("Notice: curves, acceleration patterns, and slight tremor.\n")
    
    mouse = NeuromotorMouse()
    
    # Get screen size
    screen_w, screen_h = pyautogui.size()
    
    # Define some targets to move between
    targets = [
        (screen_w // 4, screen_h // 4, 100),       # Top-left area
        (3 * screen_w // 4, screen_h // 4, 80),    # Top-right area
        (screen_w // 2, screen_h // 2, 120),       # Center
        (screen_w // 4, 3 * screen_h // 4, 60),    # Bottom-left area
        (3 * screen_w // 4, 3 * screen_h // 4, 90),# Bottom-right area
    ]
    
    for i, (x, y, target_width) in enumerate(targets):
        print(f"   Moving to target {i+1}: ({x}, {y})")
        await mouse.move_to(x, y, target_width=target_width)
        await asyncio.sleep(0.5)
    
    print("\n   ✓ Basic movement demo complete!")


async def demo_clicking():
    """Demonstrate clicking behavior."""
    print("\n" + "=" * 60)
    print("🖱️  Demo 2: Click Timing")
    print("=" * 60)
    print("\nWatch click duration and pre-click dwell time.")
    print("Timing follows log-normal distribution, not uniform!\n")
    
    mouse = NeuromotorMouse()
    screen_w, screen_h = pyautogui.size()
    
    # Move to center
    center_x, center_y = screen_w // 2, screen_h // 2
    
    print("   Single click (watch for pre-click pause)...")
    await mouse.move_to(center_x - 100, center_y, target_width=80, click=True)
    await asyncio.sleep(1)
    
    print("   Double click (watch for inter-click timing)...")
    await mouse.move_to(center_x + 100, center_y, target_width=80)
    await mouse.click(clicks=2)
    await asyncio.sleep(1)
    
    print("\n   ✓ Click demo complete!")


async def demo_speed_variations():
    """Show how Fitts' Law affects movement time."""
    print("\n" + "=" * 60)
    print("⏱️  Demo 3: Fitts' Law - Distance vs Target Size")
    print("=" * 60)
    print("\nMovement time depends on distance AND target size.")
    print("Smaller targets = slower, more careful movements.\n")
    
    # Configure with visible movements
    config = NeuromotorConfig(
        fitts=FittsParams(
            a_mean=0.300,
            b_mean=0.100,
        )
    )
    mouse = NeuromotorMouse(config)
    
    screen_w, screen_h = pyautogui.size()
    start_x = screen_w // 4
    
    # Same distance, different target sizes
    targets = [
        (3 * screen_w // 4, screen_h // 3, 150, "LARGE target (150px) - faster"),
        (3 * screen_w // 4, screen_h // 2, 50, "MEDIUM target (50px) - medium"),
        (3 * screen_w // 4, 2 * screen_h // 3, 15, "SMALL target (15px) - slower"),
    ]
    
    for end_x, end_y, target_width, description in targets:
        # First move to start position
        await mouse.move_to(start_x, end_y, target_width=100)
        await asyncio.sleep(0.3)
        
        print(f"   {description}")
        await mouse.move_to(end_x, end_y, target_width=target_width)
        await asyncio.sleep(0.8)
    
    print("\n   ✓ Fitts' Law demo complete!")


async def demo_typing():
    """Demonstrate typing behavior."""
    print("\n" + "=" * 60)
    print("⌨️  Demo 4: Human-like Typing")
    print("=" * 60)
    print("\nTyping with variable inter-key intervals.")
    print("Pauses at word boundaries, occasional thinking pauses.")
    print("\n⚠️  This will type into whatever window is focused!")
    print("   (Make sure a text editor or input field is ready)\n")
    
    response = input("   Press Enter to start typing demo (or 'skip' to skip): ")
    
    if response.lower() == 'skip':
        print("   Skipping typing demo.")
        return
    
    human = NeuromotorInput()
    
    await asyncio.sleep(2)  # Give time to focus a window
    
    text = "Hello! This is human-like typing with natural timing variations."
    print(f"   Typing: '{text}' (with typos enabled - watch for corrections!)")
    
    await human.keyboard.type_text(text, with_typos=True)
    
    print("\n   ✓ Typing demo complete!")


async def demo_diagnostics():
    """Show movement diagnostics."""
    print("\n" + "=" * 60)
    print("📊 Demo 5: Movement Diagnostics")
    print("=" * 60)
    print("\nAnalyzing movement characteristics...\n")
    
    import numpy as np
    from nothingtoseehere import FittsLaw, MinimumJerkTrajectory, PathGeometry
    
    # Simulate a movement
    fitts = FittsLaw()
    trajectory = MinimumJerkTrajectory(asymmetry=0.42)
    path_gen = PathGeometry()
    
    start = (100, 100)
    end = (700, 500)
    distance = np.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)
    duration = fitts.movement_time(distance, 50)
    
    # Generate the minimum jerk velocity profile (this has the asymmetry!)
    n_points = int(duration * 60)
    times, positions, velocities = trajectory.generate_profile(duration, 60)
    
    # Scale velocities by distance (trajectory gives normalized 0-1 positions)
    velocities_scaled = velocities * distance
    
    # Generate curved path shape
    x, y = path_gen.generate_curved_path(start, end, n_points)
    
    # Calculate metrics
    _, throughput = fitts.validate_human_plausible(distance, 50, duration)
    straightness = path_gen.straightness_index(x, y)
    
    # Peak timing from the TRAJECTORY (not path geometry)
    peak_idx = np.argmax(velocities)
    peak_timing = times[peak_idx] / duration
    
    print(f"   Movement: {distance:.0f}px distance, {duration*1000:.0f}ms duration")
    print(f"   Throughput: {throughput:.1f} bits/s (human max: ~12)")
    print(f"   Peak velocity timing: {peak_timing*100:.0f}% (human: 38-45%)")
    print(f"   Path straightness: {straightness:.3f} (human: 0.80-0.95)")
    print(f"   Peak velocity: {np.max(velocities_scaled):.0f} px/s")
    
    is_human_like = throughput < 12 and 0.35 < peak_timing < 0.55 and 0.75 < straightness < 0.98
    print(f"\n   Human-plausible: {'✓ YES' if is_human_like else '✗ NO'}")


async def main():
    print("\n" + "=" * 60)
    print("🐭 NOTHINGTOSEEHERE - Mouse Movement Demo")
    print("=" * 60)
    print("\nThis demo shows the library's human-like mouse movements.")
    print("Your actual mouse cursor will move around the screen!\n")
    
    print("Choose a demo to run:")
    print("  1. Basic mouse movements")
    print("  2. Click timing")
    print("  3. Fitts' Law (distance vs target size)")
    print("  4. Typing demo")
    print("  5. Movement diagnostics (no mouse movement)")
    print("  a. Run all demos")
    print("  q. Quit\n")
    
    choice = input("Enter choice (1-5, a, or q): ").strip().lower()
    
    if choice == 'q':
        return
    
    demos = {
        '1': demo_basic_movement,
        '2': demo_clicking,
        '3': demo_speed_variations,
        '4': demo_typing,
        '5': demo_diagnostics,
    }
    
    if choice == 'a':
        for demo in demos.values():
            await demo()
    elif choice in demos:
        await demos[choice]()
    else:
        print("Invalid choice!")
        return
    
    print("\n" + "=" * 60)
    print("✨ Demo complete!")
    print("=" * 60)
    print("\nKey characteristics of human-like movement:")
    print("  • Asymmetric velocity (peak at 38-45%, not 50%)")
    print("  • Curved paths (straightness index 0.80-0.95)")
    print("  • Signal-dependent noise (faster = more jitter)")
    print("  • Physiological tremor (8-12 Hz)")
    print("  • Throughput under 12 bits/second")
    print("  • Log-normal click durations (not uniform)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
