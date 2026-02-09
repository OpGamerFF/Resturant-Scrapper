import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def scrape_locations(locations, output_file, query_term="restaurants"):
    async with async_playwright() as p:
        # Launch browser
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        try:
            browser = await p.chromium.launch(executable_path=chrome_path, headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        except Exception as e:
            print(f"Failed to launch Chrome: {e}. Using default...")
            browser = await p.chromium.launch(headless=True)
            
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        seen_businesses = set()
        all_data = []

        for location in locations:
            print(f"\n--- Scraping {location} ---")
            search_query = f"{query_term} in {location}"
            
            try:
                await page.goto(f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}/", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5) # Give it a moment to settle
            except Exception as e:
                print(f"Navigation error for {location}: {e}")
                continue
            
            # Wait for results
            try:
                await page.wait_for_selector('a.hfpxzc', timeout=20000)
            except:
                print(f"No results found for {location}")
                continue

            # Scroll to load more
            container_selector = 'div[role="feed"]'
            for _ in range(3):
                try:
                    await page.evaluate(f'document.querySelector(\'{container_selector}\').scrollBy(0, 5000)')
                except:
                    pass
                await asyncio.sleep(2)
            
            results = await page.query_selector_all('a.hfpxzc')
            print(f"Found {len(results)} potential matches in {location}.")

            for result in results[:40]: # Checking more results since we filter for websites
                try:
                    await result.click()
                    await asyncio.sleep(2) # Wait for details
                    
                    # Extract Name - try multiple selectors
                    name = "Unknown"
                    name_selectors = ['h1.DUwDvf', 'h1.fontHeadlineLarge', 'h1.DUwDvf.lfPIob']
                    for sel in name_selectors:
                        try:
                            el = await page.query_selector(sel)
                            if el:
                                name = await el.inner_text()
                                if name and name.strip():
                                    break
                        except:
                            continue
                    
                    if name == "Unknown" or name in seen_businesses:
                        continue
                    
                    # Extract Website
                    website = "No Website"
                    website_selectors = [
                        'a[data-item-id="authority"]',
                        'a[aria-label^="Website:"]',
                        'a[aria-label*="website"]'
                    ]
                    
                    found_website = False
                    for selector in website_selectors:
                        try:
                            web_el = await page.query_selector(selector)
                            if web_el:
                                href = await web_el.get_attribute('href')
                                if href and "http" in href:
                                    website = href
                                    found_website = True
                                    break
                        except:
                            continue
                    
                    # Extract Phone
                    phone = "No Phone"
                    phone_selectors = ['button[data-tooltip="Copy phone number"]', 'a[href^="tel:"]']
                    for p_sel in phone_selectors:
                        try:
                            p_el = await page.query_selector(p_sel)
                            if p_el:
                                phone_val = await p_el.get_attribute('aria-label') or await p_el.inner_text()
                                if any(c.isdigit() for c in phone_val):
                                    phone = phone_val.replace('Phone:', '').strip()
                                    break
                        except:
                            continue

                    print(f"Added: {name} | Web: {website} | Phone: {phone}")
                    seen_businesses.add(name)
                    all_data.append(f"Name: {name} | Website: {website} | Phone: {phone}")

                except Exception as e:
                    continue

        # Save all results to one file
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in all_data:
                f.write(item + '\n')
        
        print(f"\nCompleted! Total businesses collected: {len(all_data)}")
        print(f"Data saved to {output_file}")
        await browser.close()

if __name__ == "__main__":
    locations_to_scrape = ["Gujranwala, Pakistan"]
    output = "gujranwala_data.txt"
    asyncio.run(scrape_locations(locations_to_scrape, output))
