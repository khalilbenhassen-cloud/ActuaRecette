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
        
        print("--- Inspecting stToolbar in Maximized state ---")
        toolbar = await page.query_selector('div[data-testid="stToolbar"]')
        if toolbar:
            print("stToolbar HTML:")
            print(await toolbar.inner_html())
            
            # Find all buttons inside stToolbar
            buttons = await toolbar.query_selector_all("button")
            print(f"\nFound {len(buttons)} buttons in stToolbar:")
            for i, btn in enumerate(buttons):
                testid = await btn.get_attribute("data-testid")
                classes = await btn.get_attribute("class")
                text = await btn.text_content()
                html = await btn.inner_html()
                box = await btn.bounding_box()
                print(f"  [{i}] <button data-testid=\"{testid}\" class=\"{classes}\"> at {box}: text={repr(text)}, html={repr(html)}")
        else:
            print("stToolbar not found")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
