from playwright.sync_api import sync_playwright
import pandas as pd
import re
from datetime import datetime

def scrape_property():
    with sync_playwright() as p:
        # Launch browser (headless=False for debugging)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Navigate to the URL
        url = "https://nigeriapropertycentre.com/for-sale/houses/semi-detached-duplexes/lagos/lekki/lekki-phase-1/2041871-5-bedroom-semi-detached-duplex-with-boys-quarters"
        print(f"Navigating to {url} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(1000)  # Delay to avoid bans
        except Exception as e:
            print(f"Navigation failed: {e}")
            browser.close()
            return
        
        # Wait for page to load and scroll to ensure dynamic content
        try:
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)  # Increased wait for dynamic content
        except Exception as e:
            print(f"Page load failed: {e}")
        
        # Initialize dictionary for the property
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
        
        # Try CSS selectors first
        try:
            # Extract title
            title_elem = page.locator("h1.content-title, h4.content-title").first
            if title_elem.count() > 0:
                property_data["Title"] = title_elem.inner_text().strip()
            
            # Extract address
            address_elem = page.locator("address").first
            if address_elem.count() > 0:
                property_data["Address"] = address_elem.inner_text().strip()
            
            # Extract price
            price_elements = page.locator("span.price").all()
            for elem in price_elements:
                text = elem.inner_text().strip()
                if any(char.isdigit() for char in text):
                    property_data["Price"] = text.replace("₦", "").replace("$", "").replace(",", "").strip()
                    break
            
            # Extract contact
            contact_elem = page.locator("a[href*='tel:']").first
            if contact_elem.count() > 0:
                property_data["Contact"] = contact_elem.inner_text().strip().replace("Call", "").replace("Show Phone", "").strip()
            else:
                contact_elem = page.locator("span.marketed-by").first
                if contact_elem.count() > 0:
                    property_data["Contact"] = contact_elem.inner_text().strip()
            
            # Extract photos
            photos_elem = page.locator("span.image-count").first
            photos_text = photos_elem.inner_text().strip() if photos_elem.count() > 0 else ""
            if photos_text and "of" in photos_text:
                property_data["Photos"] = photos_text.split("of")[-1].strip()
            
            # Extract property details (bedrooms, bathrooms, etc.)
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
            element.wait_for(timeout=10000)
            text_content = element.inner_text().strip()
            print(f"Description XPath Text: {text_content}")
            # Ensure the description matches the desired text
            if "A contemporary designed Five (5) Bedroom Semi-detached House" in text_content:
                property_data["Description"] = text_content
        except Exception as e:
            print(f"Description XPath failed: {e}")
        
        # Try the previous XPath for other fields as fallback
        fallback_xpath = "/html/body/div[1]/div[2]/section/div/div/div/div[1]/div[2]"
        try:
            element = page.locator(f"xpath={fallback_xpath}")
            element.wait_for(timeout=10000)
            text_content = element.inner_text().strip()
            print(f"Fallback XPath Text: {text_content}")
            lines = text_content.split("\n")
            for line in lines:
                line = line.strip()
                if "bedroom" in line.lower() and "N/A" in property_data["Title"]:
                    property_data["Title"] = line
                if "Lekki Phase 1" in line and "N/A" in property_data["Address"]:
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
        
        # Save to CSV
        df = pd.DataFrame([property_data])
        df.to_csv("properties.csv", index=False)
        print("Saved data to 'properties.csv'")
        print(f"Extracted property: {property_data['Title']}")
        
        # Close the browser
        browser.close()

if __name__ == "__main__":
    try:
        scrape_property()
    except Exception as e:
        print(f"General error: {e}")