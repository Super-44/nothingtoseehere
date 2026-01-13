#!/usr/bin/env python3
"""
Wikipedia Demo - Human-like Browser Automation

Demonstrates the nothingtoseehere library by:
1. Opening Wikipedia in a visible browser
2. Moving the mouse with human-like kinematics
3. Clicking links and typing in search
4. All movements follow neuromotor research patterns

Run with: python examples/wikipedia_demo.py
"""

import asyncio
import random
import sys
import os

# Add parent directory to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nodriver as uc
from nothingtoseehere import NeuromotorInput, NeuromotorConfig, FittsParams


async def get_element_screen_position(element, page) -> tuple[int, int, int, int]:
    """
    Get an element's position in screen coordinates.
    
    Returns (x, y, width, height) where x,y is top-left corner in screen coords.
    """
    # Get element's position within the page
    box = await element.get_position()
    
    # Get the browser window position
    # nodriver returns (WindowID, Bounds) tuple where Bounds has .left, .top, etc.
    _, bounds = await page.get_window()
    
    # Account for browser chrome (toolbar, etc.) - approximately 85px on most browsers
    chrome_height = 85
    
    screen_x = int(bounds.left + box.x)
    screen_y = int(bounds.top + chrome_height + box.y)
    
    return screen_x, screen_y, int(box.width), int(box.height)


async def main():
    print("\n" + "=" * 60)
    print("🐭 NOTHINGTOSEEHERE - Wikipedia Demo")
    print("=" * 60)
    print("\nThis demo shows human-like mouse movements and interactions.")
    print("Watch how the cursor moves with natural acceleration,")
    print("curvature, and tremor - not in straight robotic lines!\n")
    
    # Use realistic human-like defaults
    config = NeuromotorConfig(
        fitts=FittsParams(
            a_mean=0.300,  # ~300ms reaction time
            b_mean=0.100,  # ~100ms per bit
        ),
        velocity_asymmetry=0.42,
        # Using library defaults for noise/tremor (realistic human levels)
        debug_mode=False,  # Set True for slower, more visible movements
    )
    
    human = NeuromotorInput(mouse_config=config)
    
    # Launch browser - visible, not headless
    print("📖 Opening browser and navigating to Wikipedia...")
    browser = await uc.start(
        headless=False,
        browser_args=[
            '--window-size=1200,900',
            '--window-position=100,100',
        ]
    )
    
    # Get the page
    page = await browser.get('https://en.wikipedia.org')
    
    # Wait for page to load
    await asyncio.sleep(2)
    
    print("✓ Wikipedia loaded!\n")
    
    # =========================================================================
    # Demo 1: Click on "Random article" link
    # =========================================================================
    print("🎲 Demo 1: Clicking 'Random article' link...")
    
    try:
        random_link = await page.select('a[title="Load a random article [Alt+Shift+x]"]')
        if random_link:
            x, y, w, h = await get_element_screen_position(random_link, page)
            print(f"   Target: ({x}, {y}) size: {w}x{h}")
            
            await human.mouse.move_to(
                x + w // 2, 
                y + h // 2,
                target_width=w,
                target_height=h,
                click=True
            )
            print("   ✓ Clicked!")
            await asyncio.sleep(3)
    except Exception as e:
        print(f"   Could not find random article link: {e}")
    
    # =========================================================================
    # Demo 2: Go back to main page and use search
    # =========================================================================
    print("\n🔍 Demo 2: Using the search box...")
    
    await page.get('https://en.wikipedia.org')
    await asyncio.sleep(2)
    
    try:
        # Find search input
        search_input = await page.select('input[name="search"]')
        if search_input:
            x, y, w, h = await get_element_screen_position(search_input, page)
            print(f"   Search box at: ({x}, {y})")
            
            # Move to search box and click
            await human.mouse.move_to(
                x + w // 2,
                y + h // 2, 
                target_width=w,
                target_height=h,
                click=True
            )
            await asyncio.sleep(0.5)
            
            # Type a search term with human-like timing (including possible typos!)
            search_term = "Fitts's law"  # Meta! Searching for the law we're implementing
            print(f"   Typing: '{search_term}' (with realistic typos enabled)")
            await human.keyboard.type_text(search_term, with_typos=True)
            
            await asyncio.sleep(1)
            
            # Press Enter
            await human.keyboard.press_key('enter')
            print("   ✓ Search submitted!")
            await asyncio.sleep(3)
            
    except Exception as e:
        print(f"   Search failed: {e}")
    
    # =========================================================================
    # Demo 3: Scroll down the page
    # =========================================================================
    print("\n📜 Demo 3: Scrolling the page...")
    
    try:
        # Move mouse to middle of page first
        _, bounds = await page.get_window()
        center_x = bounds.left + bounds.width // 2
        center_y = bounds.top + bounds.height // 2
        
        await human.mouse.move_to(center_x, center_y, target_width=100)
        await asyncio.sleep(0.5)
        
        # Scroll down
        print("   Scrolling down...")
        await human.mouse.scroll(-5)  # Negative = scroll down
        await asyncio.sleep(1)
        
        await human.mouse.scroll(-5)
        await asyncio.sleep(1)
        
        # Scroll back up
        print("   Scrolling back up...")
        await human.mouse.scroll(3)
        await asyncio.sleep(1)
        
        print("   ✓ Scrolling complete!")
        
    except Exception as e:
        print(f"   Scrolling failed: {e}")
    
    # =========================================================================
    # Demo 4: Click on some links in the article
    # =========================================================================
    print("\n🔗 Demo 4: Clicking links in the article...")
    
    try:
        # Find links in the main content area
        links = await page.select_all('#mw-content-text a[href^="/wiki/"]')
        
        if links and len(links) > 5:
            # Click on a few random links
            for i in range(min(3, len(links))):
                # Pick a random link from the first 20
                link = random.choice(links[:20])
                
                try:
                    x, y, w, h = await get_element_screen_position(link, page)
                    
                    # Skip if element is too small or off-screen
                    if w < 10 or h < 10 or y < 100 or y > 800:
                        continue
                    
                    link_text = await link.get_property('innerText')
                    link_text = link_text[:30] + "..." if len(link_text) > 30 else link_text
                    print(f"   Clicking: '{link_text}'")
                    
                    await human.mouse.move_to(
                        x + w // 2,
                        y + h // 2,
                        target_width=max(w, 20),
                        target_height=max(h, 15),
                        click=True
                    )
                    
                    await asyncio.sleep(2)
                    
                    # Go back
                    await page.back()
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    continue
                    
            print("   ✓ Link clicking complete!")
            
    except Exception as e:
        print(f"   Link clicking failed: {e}")
    
    # =========================================================================
    # Finish
    # =========================================================================
    print("\n" + "=" * 60)
    print("✨ Demo complete!")
    print("=" * 60)
    print("\nKey things to notice:")
    print("  • Mouse movements had natural curves, not straight lines")
    print("  • Velocity peaked early in movement (38-45% mark)")
    print("  • Small tremor/jitter throughout (8-12 Hz)")
    print("  • Click targeting had slight variance (bivariate normal)")
    print("  • Typing had variable inter-key timing")
    print("\nThese patterns match human neuromotor behavior and help")
    print("evade behavioral biometric detection systems.\n")
    
    # Keep browser open for a moment
    print("Browser will close in 5 seconds...")
    await asyncio.sleep(5)
    
    browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
