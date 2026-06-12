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
        
        print("--- Finding elements in the top-right corner (x > 1000, y < 100) ---")
        
        # We can query all elements that might be buttons or interactive
        elements = await page.query_selector_all("button, a, [role='button'], div, span, ul, li")
        
        found = []
        for el in elements:
            try:
                box = await el.bounding_box()
                if box:
                    # Check if center of the bounding box is in the top-right region
                    cx = box['x'] + box['width'] / 2
                    cy = box['y'] + box['height'] / 2
                    if cx > 1000 and cy < 100:
                        tag = await el.evaluate("el => el.tagName")
                        testid = await el.get_attribute("data-testid")
                        classes = await el.get_attribute("class")
                        id_attr = await el.get_attribute("id")
                        text = await el.text_content()
                        # Print only unique elements (avoid duplicates if parent/child are both matched)
                        html_snippet = await el.evaluate("el => el.outerHTML.split('>')[0] + '>'")
                        found.append((box, tag, testid, classes, id_attr, html_snippet, text))
            except Exception:
                pass
                
        # Sort by x coordinate descending
        found = sorted(found, key=lambda item: item[0]['x'], reverse=True)
        for box, tag, testid, classes, id_attr, html_snippet, text in found[:20]:
            print(f"\nElement: {html_snippet}")
            print(f"  Tag: {tag}, TestID: {testid}, Id: {id_attr}, Classes: {classes}")
            print(f"  Bounding Box: {box}")
            print(f"  Text Content: {repr(text[:50])}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
