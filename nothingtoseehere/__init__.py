"""
nothingtoseehere - Human-like Input Simulation

A research-grounded implementation of human-like mouse and keyboard input
for browser automation. Nothing to see here, just completely normal human behavior.

Based on:
- Fitts' Law (1954): Information capacity of human motor system
- Flash & Hogan (1985): Minimum jerk trajectory model  
- Meyer et al. (1988): Two-component submovement model
- van Beers et al. (2004): Signal-dependent neuromotor noise

Key features:
- Fitts' Law movement timing (stays under 12 bits/s human ceiling)
- Asymmetric velocity profiles (peak at 38-45% of movement)
- Two-component model (ballistic + corrective submovements)
- Signal-dependent noise (scales with velocity)
- Physiological tremor (8-12 Hz spectral peak)
- Log-normal click duration distributions
- Realistic path curvature (fractal dimension 1.2-1.4)

Usage:
    from nothingtoseehere import NeuromotorInput
    
    human = NeuromotorInput()
    await human.mouse.move_to(500, 300, target_width=100, click=True)
    await human.keyboard.type_text("Hello, world!")
"""

from .neuromotor_input import (
    # Main classes
    NeuromotorMouse,
    NeuromotorKeyboard,
    NeuromotorInput,
    
    # Configuration
    NeuromotorConfig,
    FittsParams,
    ClickTimingParams,
    KeyboardTimingParams,
    ReactionTimeParams,
    
    # Component models (for advanced use)
    FittsLaw,
    MinimumJerkTrajectory,
    NeuromotorNoise,
    TwoComponentModel,
    PathGeometry,
    ClickModel,
    KeyboardModel,
    ReactionTimeModel,
    
    # Utilities
    Distributions,
    MovementDiagnostics,
    
    # Convenience functions
    human_move_and_click,
    human_type,
    
    # Type aliases
    ButtonType,
    
    # Constants (for advanced configuration)
    IS_MACOS,
    MODIFIER_KEY,
)

__version__ = "1.2.0"
__author__ = "Super44"
__all__ = [
    # Main API
    "NeuromotorMouse",
    "NeuromotorKeyboard", 
    "NeuromotorInput",
    # Configuration
    "NeuromotorConfig",
    "FittsParams",
    "ClickTimingParams",
    "KeyboardTimingParams",
    "ReactionTimeParams",
    # Component models
    "FittsLaw",
    "MinimumJerkTrajectory",
    "NeuromotorNoise",
    "TwoComponentModel",
    "PathGeometry",
    "ClickModel",
    "KeyboardModel",
    "ReactionTimeModel",
    # Utilities
    "Distributions",
    "MovementDiagnostics",
    # Convenience functions
    "human_move_and_click",
    "human_type",
    # Type aliases
    "ButtonType",
    # Constants
    "IS_MACOS",
    "MODIFIER_KEY",
]
