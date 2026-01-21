#!/usr/bin/env python3
"""
Wikipedia Demo - Human-like Browser Automation

Demonstrates the nothingtoseehere library by:
1. Searching for "Fitts's law" with human-like typing and typos
2. Scrolling the page with variable timing
3. Clicking multiple article links with natural movement
4. Searching again from article page for "Super44"
5. Toggling dark mode (simple text-based clicking)

Features showcased:
- Human-like mouse kinematics (curved paths, asymmetric velocity)
- Automatic coordinate conversion for nodriver elements
- Automatic scroll-into-view for off-screen elements
- Intelligent page load waiting with human reading time
- Auto-detected browser chrome height
- Triple-click for targeted input clearing (not global Cmd+A)
- Realistic typing with typos and corrections (15% rate for demo visibility)
- Automatic post-action delays (minimal, research-based)
- Natural browsing flow without constant homepage returns
- All movements follow neuromotor research patterns

Run with: python examples/wikipedia_demo.py

Note: The script includes automatic retry logic for intermittent browser connection issues.
"""

import asyncio
import random
import sys
import os

# Add parent directory to path for local development
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nodriver as uc
from nothingtoseehere import NeuromotorInput, NeuromotorConfig, FittsParams, KeyboardTimingParams


async def main():
    print("\n" + "=" * 60)
    print("🐭 NOTHINGTOSEEHERE - Wikipedia Demo")
    print("=" * 60)
    print("\nThis demo shows human-like mouse movements and interactions.")
    print("Watch how the cursor moves with natural acceleration,")
    print("curvature, and tremor - not in straight robotic lines!")
    print("\nDemos included:")
    print("  1. 🔍 Search with typing & typos")
    print("  2. 📜 Scrolling with variable timing")
    print("  3. 🔗 Multiple link clicks")
    print("  4. 👤 Second search from article (Super44)")
    print("  5. 🌙 Dark mode toggle")
    print()
    
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
    
    # Higher typo rate for demo visibility (default is 0.02 = 2%)
    keyboard_config = KeyboardTimingParams(
        typo_rate=0.15  # 15% chance for demo purposes - makes typos visible!
    )
    
    human = NeuromotorInput(mouse_config=config, keyboard_config=keyboard_config)
    
    # Launch browser - visible, not headless
    # Retry logic for intermittent connection issues
    print("📖 Opening browser and navigating to Wikipedia...")
    browser = None
    for attempt in range(3):
        try:
            browser = await uc.start(
                headless=False,
                browser_args=[
                    '--window-size=1200,900',
                    '--window-position=100,100',
                ]
            )
            break
        except Exception as e:
            if attempt < 2:
                print(f"   Retry {attempt + 1}/3...")
                await asyncio.sleep(1)
            else:
                print(f"\n❌ Failed to start browser after 3 attempts: {e}")
                return
    
    if not browser:
        return
    
    # Get the page
    page = await browser.get('https://en.wikipedia.org')
    await human.wait_for_page(page, min_read_time=0.5, max_read_time=1.0)
    print("✓ Wikipedia loaded!\n")
    
    # =========================================================================
    # Demo 1: Use search box
    # =========================================================================
    print("🔍 Demo 1: Using the search box...")
    print("   (Chrome height auto-detected via JavaScript)")
    
    try:
        # Find search input
        search_input = await page.select('input[name="search"]')
        if search_input:
            # Type a search term with human-like timing (including possible typos!)
            search_term = "Fitts's law"  # Meta! Searching for the law we're implementing
            print(f"   Typing: '{search_term}' (with realistic typos enabled)")
            print("   (Using triple-click to clear - more targeted than Cmd+A)")
            
            # Use the built-in fill method that handles:
            # - Click to focus
            # - Triple-click to select all (targeted, not global Cmd+A)
            # - Type with human-like timing and typos
            await human.fill_nodriver_input(search_input, page, search_term, with_typos=True)
            
            # Press Enter
            await human.keyboard.press_key('enter')
            print("   ✓ Search submitted!")
            
            # Wait for page to load and human to read
            await human.wait_for_page(page)
            
    except Exception as e:
        print(f"   Search failed: {e}")
    
    # =========================================================================
    # Demo 2: Scroll down the page
    # =========================================================================
    print("\n📜 Demo 2: Scrolling the page...")
    
    try:
        # Move mouse to middle of page first
        _, bounds = await page.get_window()
        center_x = bounds.left + bounds.width // 2
        center_y = bounds.top + bounds.height // 2
        
        await human.mouse.move_to(center_x, center_y, target_width=100)
        
        # Scroll down
        print("   Scrolling down...")
        await human.mouse.scroll(-5)  # Negative = scroll down
        await human.mouse.scroll(-5)
        
        # Scroll back up (mirror the down pattern)
        print("   Scrolling back up...")
        await human.mouse.scroll(5)
        await human.mouse.scroll(4)  # Slightly less to avoid overshooting
        
        print("   ✓ Scrolling complete!")
        
    except Exception as e:
        print(f"   Scrolling failed: {e}")
    
    # =========================================================================
    # Demo 3: Click on some links in the article
    # =========================================================================
    print("\n🔗 Demo 3: Clicking links in the article...")
    
    try:
        # Find links in the main content area
        links = await page.select_all('#mw-content-text a[href^="/wiki/"]')
        
        if links and len(links) > 5:
            # Click on a few random links
            for i in range(min(3, len(links))):
                # Pick a random link from the first 20
                link = random.choice(links[:20])
                
                try:
                    # Get element info to check if it's valid
                    box = await link.get_position()
                    
                    # Skip if element is too small or likely off-screen
                    if box.width < 10 or box.height < 10 or box.y < 0 or box.y > 700:
                        continue
                    
                    link_text = await link.get_property('innerText')
                    link_text = link_text[:30] + "..." if len(link_text) > 30 else link_text
                    print(f"   Clicking: '{link_text}'")
                    
                    await human.click_nodriver_element(link, page)
                    
                    # Wait for page to load and brief reading
                    await human.wait_for_page(page, min_read_time=0.3, max_read_time=0.8)
                    
                    # Go back
                    await page.back()
                    await human.wait_for_page(page, min_read_time=0.2, max_read_time=0.6)
                    
                except Exception as e:
                    continue
                    
            print("   ✓ Link clicking complete!")
            
    except Exception as e:
        print(f"   Link clicking failed: {e}")
    
    # =========================================================================
    # Demo 4: Search again from current page (no homepage return!)
    # =========================================================================
    print("\n👤 Demo 4: Searching for 'Super44' from article...")
    print("   (Notice we stay on the current page - more natural browsing!)")
    
    try:
        # Find search input - library will auto-scroll it into view
        search_input = await page.select('input[name="search"]')
        if search_input:
            username = "Super44"
            print(f"   Typing username: '{username}'")
            print("   (Watch the triple-click clear and realistic typing!)")
            
            # Use the improved fill method with triple-click clearing
            await human.fill_nodriver_input(
                search_input, 
                page, 
                username,
                clear_first=True,  # Uses triple-click now!
                with_typos=False   # Keep it clean for username
            )
            
            # Press Enter to search
            await human.keyboard.press_key('enter')
            print("   ✓ Search submitted!")
            
            # Wait for page to load
            await human.wait_for_page(page)
            
    except Exception as e:
        print(f"   Search demo failed: {e}")
    
    # =========================================================================
    # Demo 5: Toggle dark mode (simple text-based clicking)
    # =========================================================================
    print("\n🌙 Demo 5: Clicking 'Dark' to toggle dark mode...")
    
    try:
        # Simply click on text "Dark"
        dark_option = await page.find('Dark', timeout=3)
        await human.click_nodriver_element(dark_option, page)
        print("   ✓ Dark mode toggled!")
                
    except Exception as e:
        print(f"   (Skipped - Dark option not found: {e})")
    
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
    print("  • Triple-click for targeted input clearing (not global Cmd+A)")
    print("  • Chrome height auto-detected for accurate clicking")
    print("  • Automatic post-action delays (minimal, research-based)")
    print("  • Elements automatically scroll into view before clicking")
    print("  • Intelligent page load waiting + human reading time")
    print("\nThese patterns match human neuromotor behavior and help")
    print("evade behavioral biometric detection systems.\n")
    
    # Keep browser open for a moment
    print("Browser will close in 5 seconds...")
    await asyncio.sleep(5)
    
    # Clean shutdown
    try:
        browser.stop()
        await asyncio.sleep(1)  # Give it time to clean up
    except Exception:
        pass  # Ignore cleanup errors


if __name__ == "__main__":
    asyncio.run(main())
