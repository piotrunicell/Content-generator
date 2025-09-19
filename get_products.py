from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from pyairtable import Table
from math import ceil
import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import logging



def main():
    print("call initiated")

    load_dotenv()

    AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
    AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
    AIRTABLE_TABLE_NAME = 'products'


    # Change to your chromedriver path if necessary
    chrome_options = webdriver.ChromeOptions()
    chrome_options.set_capability('browserless:token', os.environ['BROWSER_TOKEN'])
    # Set args similar to puppeteer's for best performance
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-component-extensions-with-background-pages")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
    chrome_options.add_argument("--force-color-profile=srgb")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Remote(
        command_executor=os.environ['BROWSER_WEBDRIVER_ENDPOINT'],
        options=chrome_options
    )
    WebDriverWait(driver, 15)
    logging.basicConfig(level=logging.INFO)
    logging.info("browser launched")
    # Step 1: Go to the collections page
    COLLECTION_URL = "https://primacol.com/en-pl/collections/collections"
    driver.get(COLLECTION_URL)

    # Step 2: Wait for the product grid to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/products/']"))
    )

    # Step 3: Extract product links from the collections page
    product_links = set()
    products = driver.find_elements(By.CSS_SELECTOR, "menu-dropdown a[href*='/products/']:not(.card__colors a):not(.card__colors *)")

    for p in products:
        url = p.get_attribute("href")
        if url:
            product_links.add(url)

    all_data = []
    # Step 4: Scrape details from each individual product page
    logging.info(f"Found {len(product_links)} products. Scraping details...")
    print(f"Found {len(product_links)} products. Scraping details...")
    for link in product_links:
        driver.get(link)
        try:
            time.sleep(5)
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-product-name], h1, .product__title, .product__description, .summary__title h3, .accordion__content.rte"))
            )

            for elem in driver.find_elements(By.CSS_SELECTOR, ".summary__title h3"):
                if not elem.text.strip().lower().startswith("5."):
                    elem.click()
            name = driver.find_element(By.TAG_NAME, "h1").text
            desc_blocks = driver.find_elements(By.CSS_SELECTOR, ".product__description, .summary__title h3, .accordion__content.rte")
            
            description = "\n".join([
                el.text for el in desc_blocks
                if el.text.strip() and not el.text.strip().startswith("5.")
            ])
            print(description)

            color_blocks = driver.find_elements(By.CSS_SELECTOR, ".color__swatch-tooltip")
            print(f"Found {len(color_blocks)} colors")
            colors = ", ".join([el.get_attribute("textContent") for el in color_blocks])
            print(colors)
            # Any additional selectors for details:
            # For example: price, image, availability, etc.
            item = {"line": name, "colorways": colors, "updated": datetime.now().strftime("%Y-%m-%d"), "description": description, "url": link}
            all_data.append(item)
        except Exception:
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!Failed to scrape {link}")
            continue
        

    driver.quit()

    # Print or save the results
    for row in all_data:
        print(row)
    logging.info(f"uploading {len(all_data)} records to Airtable")
    table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

    batch_size = 10
    num_batches = ceil(len(all_data) / batch_size)
    for i in range(num_batches):
        batch = all_data[i * batch_size: (i + 1) * batch_size]
        table.batch_create(batch)  # add typecast=True if you want Airtable to auto-convert types

if __name__ == "__main__":
    main()