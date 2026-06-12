import asyncio
import os
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1200, "height": 800})
        
        print("Navigating to http://localhost:8501 ...")
        await page.goto("http://localhost:8501")
        await page.wait_for_timeout(5000)
        
        # Take screenshot of login page
        screenshot_path = "C:/Users/hp/.gemini/antigravity/brain/7a7f28f3-fd5e-4847-b8f4-5d95e6215948/scratch/login_page.png"
        await page.screenshot(path=screenshot_path)
        print(f"Saved login screenshot to {screenshot_path}")
        
        # Print main body HTML
        body = await page.query_selector("body")
        body_html = await body.inner_html() if body else "No body"
        print("Body length:", len(body_html))
        
        # Print elements with data-testid
        elements = await page.query_selector_all("[data-testid]")
        print("Elements with data-testid:")
        for el in elements:
            testid = await el.get_attribute("data-testid")
            tag_name = await el.evaluate("el => el.tagName")
            print(f"  <{tag_name} data-testid=\"{testid}\">")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
