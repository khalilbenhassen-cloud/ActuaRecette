import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1200, "height": 800})
        
        await page.goto("http://localhost:8501")
        await page.wait_for_selector('button[data-testid="stBaseButton-secondaryFormSubmit"]')
        await page.click('button[data-testid="stBaseButton-secondaryFormSubmit"]')
        await page.wait_for_timeout(5000)
        
        # Collapse the sidebar by resizing
        await page.set_viewport_size({"width": 500, "height": 800})
        await page.wait_for_timeout(3000)
        
        print("\n--- Inspecting Expand Button when Collapsed ---")
        button = await page.query_selector('button[data-testid="stExpandSidebarButton"]')
        if button:
            is_visible = await button.is_visible()
            box = await button.bounding_box()
            computed_style = await button.evaluate("""el => {
                const computed = window.getComputedStyle(el);
                return {
                    display: computed.display,
                    visibility: computed.visibility,
                    opacity: computed.opacity,
                    width: computed.width,
                    height: computed.height,
                    pointerEvents: computed.pointerEvents,
                    color: computed.color
                };
            }""")
            print("Button is_visible:", is_visible)
            print("Button bounding box:", box)
            print("Button computed style:", computed_style)
            
            # Print computed style of its parent elements up to stToolbar
            parent = await button.evaluate_handle("el => el.parentElement")
            while parent:
                tag = await parent.evaluate("el => el.tagName")
                testid = await parent.evaluate("el => el.getAttribute('data-testid')")
                styles = await parent.evaluate("""el => {
                    const computed = window.getComputedStyle(el);
                    return {
                        display: computed.display,
                        visibility: computed.visibility,
                        opacity: computed.opacity,
                        pointerEvents: computed.pointerEvents,
                        width: computed.width,
                        height: computed.height
                    };
                }""")
                print(f"Parent <{tag} data-testid=\"{testid}\"> styles:", styles)
                if testid == "stToolbar":
                    break
                parent = await parent.evaluate_handle("el => el.parentElement")
        else:
            print("Button button[data-testid=\"stExpandSidebarButton\"] NOT found in DOM!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
