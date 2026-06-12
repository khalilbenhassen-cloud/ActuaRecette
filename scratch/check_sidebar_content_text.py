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
        
        # Query sidebar text content
        sidebar = await page.query_selector('section[data-testid="stSidebar"]')
        if sidebar:
            text = await sidebar.text_content()
            print("--- SIDEBAR TEXT CONTENT ---")
            print(text)
            
            # Print children tag names and classes
            print("\n--- SIDEBAR CHILDREN ---")
            children = await sidebar.query_selector_all("*")
            print(f"Total elements inside sidebar: {len(children)}")
            for i, child in enumerate(children[:25]):
                tag = await child.evaluate("el => el.tagName")
                testid = await child.get_attribute("data-testid")
                classes = await child.get_attribute("class")
                text_snippet = await child.text_content()
                snippet = text_snippet[:30] if text_snippet else ""
                print(f"  [{i}] <{tag} data-testid=\"{testid}\" class=\"{classes}\">: {repr(snippet)}")
        else:
            print("Sidebar NOT found in DOM")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
