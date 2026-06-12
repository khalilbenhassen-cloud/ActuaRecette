import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        # Launch browser headlessly
        browser = await p.chromium.launch(headless=True)
        # Create a page
        page = await browser.new_page()
        # Set initial size to wide
        await page.set_viewport_size({"width": 1200, "height": 800})
        
        print("Navigating to http://localhost:8501 ...")
        await page.goto("http://localhost:8501")
        # Wait for the login page button to appear
        await page.wait_for_selector('button[data-testid="stBaseButton-secondaryFormSubmit"]')
        
        # Click "Se connecter" button (the first user in selectbox is selected by default)
        print("Clicking Se connecter button...")
        await page.click('button[data-testid="stBaseButton-secondaryFormSubmit"]')
        
        # Wait for dashboard to load
        print("Waiting for dashboard to load...")
        await page.wait_for_timeout(5000)
        
        # Save a screenshot of the main dashboard expanded
        os.makedirs("C:/Users/hp/.gemini/antigravity/brain/7a7f28f3-fd5e-4847-b8f4-5d95e6215948/scratch", exist_ok=True)
        await page.screenshot(path="C:/Users/hp/.gemini/antigravity/brain/7a7f28f3-fd5e-4847-b8f4-5d95e6215948/scratch/dashboard_expanded.png")
        print("Saved dashboard_expanded.png")
        
        # Check if the sidebar is expanded
        sidebar = await page.query_selector('section[data-testid="stSidebar"]')
        if sidebar:
            width = await sidebar.evaluate("el => el.getBoundingClientRect().width")
            outer_html = await sidebar.evaluate("el => el.outerHTML.split('>')[0] + '>'")
            print(f"Expanded Sidebar outer tag: {outer_html}")
            print(f"Expanded Sidebar width: {width}")
        else:
            print("Sidebar not found when expanded")
            
        # Resize to narrow window (e.g., width 500, height 800)
        print("Resizing to narrow window...")
        await page.set_viewport_size({"width": 500, "height": 800})
        await page.wait_for_timeout(3000)
        
        # Save a screenshot of the collapsed layout on narrow screen
        await page.screenshot(path="C:/Users/hp/.gemini/antigravity/brain/7a7f28f3-fd5e-4847-b8f4-5d95e6215948/scratch/dashboard_collapsed_narrow.png")
        print("Saved dashboard_collapsed_narrow.png")
        
        if sidebar:
            width = await sidebar.evaluate("el => el.getBoundingClientRect().width")
            outer_html = await sidebar.evaluate("el => el.outerHTML.split('>')[0] + '>'")
            print(f"Collapsed Sidebar outer tag: {outer_html}")
            print(f"Collapsed Sidebar width: {width}")
            
        # Print HTML of the header, toolbar, and sidebar elements when collapsed
        print("\n=== STHEADER HTML (Collapsed) ===")
        header = await page.query_selector('header[data-testid="stHeader"]')
        if header:
            print(await header.inner_html())
        else:
            print("stHeader not found")
            
        print("\n=== COLLAPSED CONTROL (Expand chevron) ===")
        control = await page.query_selector('[data-testid="stSidebarCollapsedControl"]')
        if not control:
            control = await page.query_selector('[data-testid="collapsedControl"]')
        if control:
            print("Control HTML:", await control.inner_html())
            is_visible = await control.is_visible()
            print("Control is_visible:", is_visible)
            box = await control.bounding_box()
            print("Control bounding box:", box)
        else:
            print("Control not found")
            
        print("\n=== STTOOLBAR HTML (Collapsed) ===")
        toolbar = await page.query_selector('div[data-testid="stToolbar"]')
        if toolbar:
            print(await toolbar.inner_html())
        else:
            print("stToolbar not found")
            
        # Resize back to wide (e.g. 1200 x 800)
        print("\nResizing back to wide (maximizing window)...")
        await page.set_viewport_size({"width": 1200, "height": 800})
        await page.wait_for_timeout(3000)
        
        # Save a screenshot of the dashboard after maximizing (is sidebar visible?)
        await page.screenshot(path="C:/Users/hp/.gemini/antigravity/brain/7a7f28f3-fd5e-4847-b8f4-5d95e6215948/scratch/dashboard_maximized.png")
        print("Saved dashboard_maximized.png")
        
        # Check if the sidebar is expanded or collapsed after maximizing
        if sidebar:
            width = await sidebar.evaluate("el => el.getBoundingClientRect().width")
            outer_html = await sidebar.evaluate("el => el.outerHTML.split('>')[0] + '>'")
            print(f"Maximized Sidebar outer tag: {outer_html}")
            print(f"Maximized Sidebar width: {width}")
            
        # Let's check control again after maximizing
        control_max = await page.query_selector('[data-testid="stSidebarCollapsedControl"]')
        if not control_max:
            control_max = await page.query_selector('[data-testid="collapsedControl"]')
        if control_max:
            is_visible_max = await control_max.is_visible()
            print("Maximized control is_visible:", is_visible_max)
            box_max = await control_max.bounding_box()
            print("Maximized control bounding box:", box_max)
        else:
            print("Maximized control not found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
