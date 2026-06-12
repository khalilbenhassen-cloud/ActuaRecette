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
        
        print("--- Inspecting elements in stHeader / stToolbar ---")
        
        # Query stHeader
        header = await page.query_selector('header[data-testid="stHeader"]')
        if header:
            print("\nHeader HTML:")
            print(await header.inner_html())
            
            # Query all buttons and interactive elements in header
            elements = await header.query_selector_all("button, [role='button'], div[data-testid]")
            print(f"\nFound {len(elements)} elements in header:")
            for i, el in enumerate(elements):
                tag = await el.evaluate("el => el.tagName")
                testid = await el.get_attribute("data-testid")
                classes = await el.get_attribute("class")
                text = await el.text_content()
                box = await el.bounding_box()
                print(f"  [{i}] <{tag} data-testid=\"{testid}\" class=\"{classes}\"> at {box}: {repr(text)}")
        else:
            print("stHeader not found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
