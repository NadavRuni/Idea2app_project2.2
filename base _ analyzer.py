import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# Constants
CSV_FILE_PATH = 'input/military_bases.csv'  # Path to the CSV file
ROWS_TO_PROCESS = 5                         # Number of rows to process
SCREENSHOTS_FOLDER = 'screen_shots'          # Folder to save screenshots

# Read the CSV into a DataFrame
df = pd.read_csv(CSV_FILE_PATH)

# Set up Chrome browser options (we want the browser visible for debugging)
chrome_options = Options()

# Do NOT enable headless mode so we can see the browser
# chrome_options.add_argument('--headless')

# Create the Chrome driver (make sure you have chromedriver installed)
service = Service()  # You can specify chromedriver path here if needed
driver = webdriver.Chrome(service=service, options=chrome_options)

# Loop over the first 5 rows
for idx, row in df.head(ROWS_TO_PROCESS).iterrows():
    latitude = row['latitude']    # Get latitude from the CSV row
    longitude = row['longitude']  # Get longitude from the CSV row

    # Build the Google Earth URL for the location
    url = f"https://earth.google.com/web/@{latitude},{longitude},1000a,35y,0h,0t,0r"
    print(f"Opening {url}")
    driver.get(url)

    # Wait for the page to fully load (otherwise screenshot might be blank)
    time.sleep(10)

    # Take a screenshot and save it
    screenshot_path = f"{SCREENSHOTS_FOLDER}/screenshot_{idx}.png"
    driver.save_screenshot(screenshot_path)
    print(f"Saved screenshot to {screenshot_path}")

# Close the browser
driver.quit()
