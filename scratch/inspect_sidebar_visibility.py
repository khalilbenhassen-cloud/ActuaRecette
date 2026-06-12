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
        
        async def print_sidebar_computed_styles(stage):
            print(f"\n--- Stage: {stage} ---")
            sidebar = await page.query_selector('section[data-testid="stSidebar"]')
            if not sidebar:
                print("Sidebar element not found in DOM!")
                return
                
            style = await sidebar.evaluate("""el => {
                const computed = window.getComputedStyle(el);
                return {
                    display: computed.display,
                    visibility: computed.visibility,
                    width: computed.width,
                    minWidth: computed.minWidth,
                    maxWidth: computed.maxWidth,
                    marginLeft: computed.marginLeft,
                    marginRight: computed.marginRight,
                    transform: computed.transform,
                    position: computed.position,
                    opacity: computed.opacity,
                    zIndex: computed.zIndex,
                    left: computed.left
                };
            }""")
            print("Computed Styles:", style)
            
            # Print parent app view container width & layout
            app_container = await page.query_selector('div[data-testid="stAppViewContainer"]')
            if app_container:
                container_style = await app_container.evaluate("""el => {
                    const computed = window.getComputedStyle(el);
                    return {
                        display: computed.display,
                        flexDirection: computed.flexDirection
                    };
                }""")
                print("AppViewContainer Style:", container_style)

        await print_sidebar_computed_styles("1. Initial Maximized")
        
        # Resize to narrow
        await page.set_viewport_size({"width": 500, "height": 800})
        await page.wait_for_timeout(3000)
        await print_sidebar_computed_styles("2. Collapsed (Narrow)")
        
        # Resize to wide
        await page.set_viewport_size({"width": 1200, "height": 800})
        await page.wait_for_timeout(3000)
        await print_sidebar_computed_styles("3. Maximized again")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
