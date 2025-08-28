from playwright.sync_api import sync_playwright
import pandas as pd
import re
from datetime import datetime
import time
import random
import os

def scrape_all_properties():
    with sync_playwright() as p:
        # Launch browser (headless=False for debugging)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Start from the search page
        search_url = "https://nigeriapropertycentre.com/for-sale/lagos?selectedLoc=1&q=for-sale+lagos"
        print(f"Navigating to search page: {search_url} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            page.goto(search_url, timeout=90000)
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f"Navigation failed: {e}")
            browser.close()
            return
        
        # Wait for page to load and scroll
        try:
            page.wait_for_load_state("domcontentloaded", timeout=90000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(5000)
        except Exception as e:
            print(f"Page load failed: {e}")
        
        # Initialize list for all properties
        all_properties = []
        csv_file = "properties.csv"
        
        # Load existing CSV if it exists
        if os.path.exists(csv_file):
            try:
                existing_df = pd.read_csv(csv_file, encoding='utf-8')
                all_properties = existing_df.to_dict('records')
                print(f"Loaded {len(all_properties)} existing properties from {csv_file}")
            except Exception as e:
                print(f"Failed to load existing CSV: {e}")
                all_properties = []
        
        # Load last scraped page
        last_page_file = "last_page.txt"
        start_page = 1
        if os.path.exists(last_page_file):
            try:
                with open(last_page_file, 'r') as f:
                    start_page = int(f.read().strip()) + 1
                print(f"Resuming from page {start_page}")
            except Exception as e:
                print(f"Failed to read last page: {e}")
                start_page = 1
        
        page_number = start_page
        max_listings = 5000
        
        # Navigate to starting page
        if page_number > 1:
            try:
                page.goto(f"{search_url}&page={page_number}", timeout=90000)
                page.wait_for_timeout(1000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Failed to navigate to page {page_number}: {e}")
                browser.close()
                return
        
        while True:
            if len(all_properties) >= max_listings:
                print(f"Reached max listings limit ({max_listings})")
                break
            
            print(f"Scraping page {page_number}")
            
            # Extract detail links from current page
            detail_links = []
            try:
                listings = page.locator(".wp-block-content").all()
                for listing in listings:
                    link = listing.locator("a:has(h4.content-title)").get_attribute("href") if listing.locator("a:has(h4.content-title)").count() > 0 else None
                    if link:
                        detail_links.append(f"https://nigeriapropertycentre.com{link}")
                print(f"Found {len(detail_links)} listings on page {page_number}")
            except Exception as e:
                print(f"Failed to extract links on page {page_number}: {e}")
            
            # Scrape each detail page
            for detail_url in detail_links:
                print(f"Scraping detail page: {detail_url}")
                for attempt in range(3):
                    property_data = scrape_detail_page(browser, detail_url)
                    if property_data:
                        all_properties.append(property_data)
                        break
                    print(f"Retry {attempt + 1}/3 for {detail_url}")
                    time.sleep(random.uniform(2, 5))
                
                # Save incrementally after each detail page
                if all_properties:
                    try:
                        df = pd.DataFrame(all_properties)
                        df.to_csv(csv_file, index=False, encoding='utf-8')
                        print(f"Saved {len(all_properties)} properties to {csv_file}")
                    except Exception as e:
                        print(f"Failed to save CSV: {e}")
                time.sleep(random.uniform(2, 5))
            
            print(f"Total properties collected so far: {len(all_properties)}")
            
            # Save current page number
            try:
                with open(last_page_file, 'w') as f:
                    f.write(str(page_number))
                print(f"Saved page {page_number} to {last_page_file}")
            except Exception as e:
                print(f"Failed to save page number: {e}")
            
            # Check for next page
            next_page_elem = page.locator("a.pagination-next, a[rel='next']").first
            if next_page_elem.count() > 0:
                next_url = next_page_elem.get_attribute("href")
                print(f"Next page URL: {next_url}")
                if next_url:
                    for attempt in range(3):
                        try:
                            page.goto(f"https://nigeriapropertycentre.com{next_url}", timeout=90000)
                            page.wait_for_timeout(1000)
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(5000)
                            page_number += 1
                            break
                        except Exception as e:
                            print(f"Next page navigation failed (attempt {attempt + 1}/3): {e}")
                            time.sleep(random.uniform(2, 5))
                    else:
                        print("Failed to navigate to next page after retries")
                        break
                else:
                    print("No next page URL found")
                    break
            else:
                print("No next page button found")
                break
        
        # Final save
        if all_properties:
            try:
                df = pd.DataFrame(all_properties)
                df.to_csv(csv_file, index=False, encoding='utf-8')
                print(f"Final save: {len(all_properties)} properties to {csv_file}")
            except Exception as e:
                print(f"Final CSV save failed: {e}")
        else:
            print("No properties found")
        
        # Close the browser
        browser.close()

def scrape_detail_page(browser, url):
    page = browser.new_page()
    try:
        page.goto(url, timeout=90000)
        page.wait_for_timeout(1000)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(5000)
    except Exception as e:
        print(f"Detail page navigation failed: {e}")
        page.close()
        return None
    
    property_data = {
        "Title": "N/A",
        "Address": "N/A",
        "Price": "N/A",
        "Description": "N/A",
        "Contact": "N/A",
        "Photos": "N/A",
        "Link": url,
        "Bedrooms": "N/A",
        "Bathrooms": "N/A",
        "Toilets": "N/A",
        "Parking Spaces": "N/A"
    }
    
    # Try CSS selectors
    try:
        title_elem = page.locator("h1.content-title, h4.content-title").first
        if title_elem.count() > 0:
            property_data["Title"] = title_elem.inner_text().strip()
        
        address_elem = page.locator("address").first
        if address_elem.count() > 0:
            property_data["Address"] = address_elem.inner_text().strip()
        
        price_elements = page.locator("span.price").all()
        for elem in price_elements:
            text = elem.inner_text().strip()
            if any(char.isdigit() for char in text):
                property_data["Price"] = text.replace("₦", "").replace("$", "").replace(",", "").strip()
                break
        
        contact_elem = page.locator("a[href*='tel:']").first
        if contact_elem.count() > 0:
            property_data["Contact"] = contact_elem.inner_text().strip().replace("Call", "").replace("Show Phone", "").strip()
        else:
            contact_elem = page.locator("span.marketed-by").first
            if contact_elem.count() > 0:
                property_data["Contact"] = contact_elem.inner_text().strip()
        
        photos_elem = page.locator("span.image-count").first
        photos_text = photos_elem.inner_text().strip() if photos_elem.count() > 0 else ""
        if photos_text and "of" in photos_text:
            property_data["Photos"] = photos_text.split("of")[-1].strip()
        
        details = page.locator(".wp-block-table table tr, .specifications tr").all()
        for detail in details:
            label = detail.locator("td").first.inner_text().strip().lower()
            value = detail.locator("td").nth(1).inner_text().strip()
            if "bedroom" in label:
                property_data["Bedrooms"] = re.search(r'\d+', value).group() if re.search(r'\d+', value) else "N/A"
            elif "bathroom" in label:
                property_data["Bathrooms"] = re.search(r'\d+', value).group() if re.search(r'\d+', value) else "N/A"
            elif "toilet" in label:
                property_data["Toilets"] = re.search(r'\d+', value).group() if re.search(r'\d+', value) else "N/A"
            elif "parking" in label:
                property_data["Parking Spaces"] = re.search(r'\d+', value).group() if re.search(r'\d+', value) else "N/A"
    
    except Exception as e:
        print(f"CSS selector extraction failed: {e}")
    
    # Try the new XPath for description
    description_xpath = "/html/body/div[1]/div[2]/section/div/div/div/div[1]/div[2]/div[4]/div/div/div/div[1]/div"
    try:
        element = page.locator(f"xpath={description_xpath}")
        element.wait_for(timeout=20000)
        text_content = element.inner_text().strip()
        print(f"Description XPath Text: {text_content[:100]}...")
        property_data["Description"] = text_content
    except Exception as e:
        print(f"Description XPath failed: {e}")
        try:
            description_elem = page.locator("div[itemprop='description']").first
            if description_elem.count() > 0:
                property_data["Description"] = description_elem.inner_text().strip()
        except Exception as e:
            print(f"CSS description fallback failed: {e}")
    
    # Try the fallback XPath for other fields
    fallback_xpath = "/html/body/div[1]/div[2]/section/div/div/div/div[1]/div[2]"
    try:
        element = page.locator(f"xpath={fallback_xpath}")
        element.wait_for(timeout=20000)
        text_content = element.inner_text().strip()
        print(f"Fallback XPath Text: {text_content[:100]}...")
        lines = text_content.split("\n")
        for line in lines:
            line = line.strip()
            if "bedroom" in line.lower() and "N/A" in property_data["Title"]:
                property_data["Title"] = line
            if any(x in line for x in ["Lagos", "Lekki", "Ikoyi"]) and "N/A" in property_data["Address"]:
                property_data["Address"] = line
            if "₦" in line and "N/A" in property_data["Price"]:
                property_data["Price"] = line.replace("₦", "").replace(",", "").strip()
            if any(c.isdigit() for c in line) and "Call" in line and "N/A" in property_data["Contact"]:
                property_data["Contact"] = line.replace("Call", "").replace("Show Phone", "").strip()
            if "of" in line and any(c.isdigit() for c in line) and "N/A" in property_data["Photos"]:
                property_data["Photos"] = line.split("of")[-1].strip()
            if "Bedrooms" in line and any(c.isdigit() for c in line):
                property_data["Bedrooms"] = re.search(r'\d+', line).group() if re.search(r'\d+', line) else "N/A"
            if "Bathrooms" in line and any(c.isdigit() for c in line):
                property_data["Bathrooms"] = re.search(r'\d+', line).group() if re.search(r'\d+', line) else "N/A"
            if "Toilets" in line and any(c.isdigit() for c in line):
                property_data["Toilets"] = re.search(r'\d+', line).group() if re.search(r'\d+', line) else "N/A"
            if "Parking Spaces" in line and any(c.isdigit() for c in line):
                property_data["Parking Spaces"] = re.search(r'\d+', line).group() if re.search(r'\d+', line) else "N/A"
    except Exception as e:
        print(f"Fallback XPath failed: {e}")
    
    # Close the detail page
    page.close()
    
    return property_data

if __name__ == "__main__":
    try:
        scrape_all_properties()
    except Exception as e:
        print(f"General error: {e}")