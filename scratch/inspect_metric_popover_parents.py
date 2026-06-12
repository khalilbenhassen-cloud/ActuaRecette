import asyncio
import sys
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1200, "height": 800})
        
        await page.goto("http://localhost:8501")
        await page.wait_for_selector('button[data-testid="stBaseButton-secondaryFormSubmit"]')
        await page.click('button[data-testid="stBaseButton-secondaryFormSubmit"]')
        await page.wait_for_timeout(5000)
        
        print("--- Inspecting Metric Popover Ancestors ---")
        
        # Query all popovers
        popovers = await page.query_selector_all('div[data-testid="stPopover"]')
        target_popover = None
        
        for pop in popovers:
            box = await pop.bounding_box()
            if box and box['x'] > 1000 and box['y'] < 100:
                target_popover = pop
                print(f"Target Popover found at box: {box}")
                break
                
        if target_popover:
            # Walk up the DOM tree and print styles of each parent
            parent = await target_popover.evaluate_handle("el => el.parentElement")
            while parent:
                tag = await parent.evaluate("el => el.tagName")
                testid = await parent.evaluate("el => el.getAttribute('data-testid')")
                classes = await parent.evaluate("el => el.getAttribute('class')")
                style = await parent.evaluate("""el => {
                    const computed = window.getComputedStyle(el);
                    return {
                        position: computed.position,
                        left: computed.left,
                        top: computed.top,
                        width: computed.width,
                        height: computed.height
                    };
                }""")
                outer_tag = await parent.evaluate("el => el.outerHTML.split('>')[0] + '>'")
                print(f"\nParent: {outer_tag}")
                print(f"  Tag: {tag}, TestID: {testid}, Classes: {classes}")
                print(f"  Computed position/size: {style}")
                
                if tag == "BODY":
                    break
                parent = await parent.evaluate_handle("el => el.parentElement")
        else:
            print("Target popover at top-right not found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
