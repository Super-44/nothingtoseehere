#!/usr/bin/env python3
"""
Wikipedia Demo - Human-like Browser Automation

Demonstrates the nothingtoseehere library by:
1. Clicking on "Random article" with accurate targeting
2. Searching for "Fitts's law" with human-like typing and typos
3. Scrolling the page with variable timing
4. Clicking multiple article links with natural movement
5. Toggling dark mode (UI element interaction)
6. Typing custom username "Super44" with triple-click clearing

Features showcased:
- Human-like mouse kinematics (curved paths, asymmetric velocity)
- Auto-detected browser chrome height
- Triple-click for targeted input clearing (not global Cmd+A)
- Realistic typing with typos and corrections
- All movements follow neuromotor research patterns

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


async def main():
    print("\n" + "=" * 60)
    print("🐭 NOTHINGTOSEEHERE - Wikipedia Demo")
    print("=" * 60)
    print("\nThis demo shows human-like mouse movements and interactions.")
    print("Watch how the cursor moves with natural acceleration,")
    print("curvature, and tremor - not in straight robotic lines!")
    print("\nDemos included:")
    print("  1. 🎲 Random article click")
    print("  2. 🔍 Search with typing & typos")
    print("  3. 📜 Scrolling with variable timing")
    print("  4. 🔗 Multiple link clicks")
    print("  5. 🌙 Dark mode toggle")
    print("  6. 👤 Custom username search (Super44)")
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
    print("   (Chrome height auto-detected via JavaScript)")
    
    try:
        random_link = await page.select('a[title="Load a random article [Alt+Shift+x]"]')
        if random_link:
            print(f"   Found random article link, clicking...")
            # Note: chrome_height is auto-detected by default
            # For maximum reliability, you can use: use_cdp_click=True
            await human.click_nodriver_element(random_link, page)
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
            # Type a search term with human-like timing (including possible typos!)
            search_term = "Fitts's law"  # Meta! Searching for the law we're implementing
            print(f"   Typing: '{search_term}' (with realistic typos enabled)")
            print("   (Using triple-click to clear - more targeted than Cmd+A)")
            
            # Use the built-in fill method that handles:
            # - Click to focus
            # - Triple-click to select all (targeted, not global Cmd+A)
            # - Type with human-like timing and typos
            await human.fill_nodriver_input(search_input, page, search_term, with_typos=True)
            
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
                    # Get element info to check if it's valid
                    box = await link.get_position()
                    
                    # Skip if element is too small or likely off-screen
                    if box.width < 10 or box.height < 10 or box.y < 0 or box.y > 700:
                        continue
                    
                    link_text = await link.get_property('innerText')
                    link_text = link_text[:30] + "..." if len(link_text) > 30 else link_text
                    print(f"   Clicking: '{link_text}'")
                    
                    await human.click_nodriver_element(link, page)
                    
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
    # Demo 5: Toggle dark mode
    # =========================================================================
    print("\n🌙 Demo 5: Toggling dark mode...")
    
    try:
        # Navigate to main page first
        await page.get('https://en.wikipedia.org')
        await asyncio.sleep(2)
        
        # Look for the appearance/theme toggle button
        # Wikipedia's theme toggle can be in different places depending on login state
        # Try common selectors
        theme_selectors = [
            'button[title*="appearance"]',
            'button[title*="theme"]',
            'a[title*="appearance"]',
            '#vector-appearance-dropdown-checkbox',
            '.vector-appearance-landmark button',
        ]
        
        theme_button = None
        for selector in theme_selectors:
            try:
                theme_button = await page.select(selector, timeout=1)
                if theme_button:
                    break
            except Exception:
                continue
        
        if theme_button:
            print("   Found theme toggle button, clicking...")
            await human.click_nodriver_element(theme_button, page)
            await asyncio.sleep(0.5)
            
            # Try to click on dark mode option if menu appeared
            try:
                dark_mode_option = await page.select('input[value="night"], button:has-text("Dark")', timeout=1)
                if dark_mode_option:
                    print("   Clicking dark mode option...")
                    await human.click_nodriver_element(dark_mode_option, page)
                    await asyncio.sleep(1)
                    print("   ✓ Dark mode toggled!")
            except Exception:
                print("   ✓ Theme menu opened!")
        else:
            print("   Theme toggle not found (may vary by Wikipedia version)")
            
    except Exception as e:
        print(f"   Theme toggle demo skipped: {e}")
    
    # =========================================================================
    # Demo 6: Search with custom username
    # =========================================================================
    print("\n👤 Demo 6: Searching for 'Super44'...")
    
    try:
        # Navigate to main page to ensure we have a fresh search box
        await page.get('https://en.wikipedia.org')
        await asyncio.sleep(2)
        
        # Find search input
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
            
            await asyncio.sleep(0.5)
            
            # Press Enter to search
            await human.keyboard.press_key('enter')
            print("   ✓ Search submitted!")
            await asyncio.sleep(2)
            
    except Exception as e:
        print(f"   Username search demo failed: {e}")
    
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
    print("\nThese patterns match human neuromotor behavior and help")
    print("evade behavioral biometric detection systems.\n")
    
    # Keep browser open for a moment
    print("Browser will close in 5 seconds...")
    await asyncio.sleep(5)
    
    browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
