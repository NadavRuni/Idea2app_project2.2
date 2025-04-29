from typing import Any

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from PIL import Image
from google import genai
from dotenv import load_dotenv
import os
import json
import json
from typing import List

def extract_findings_from_response_text(response_text: str) -> List[str]:
    """
    Extracts the 'findings' list from a JSON-formatted response string.

    Args:
        response_text (str): The raw response text from Gemini (may contain ```json ... ``` markers).

    Returns:
        List[str]: A list of findings extracted from the response.

    Raises:
        KeyError: If 'findings' field is missing.
        json.JSONDecodeError: If the text is not valid JSON.
    """
    # Clean if wrapped with ```json ... ```
    if response_text.strip().startswith('```json'):
        response_text = response_text.strip()[7:-3].strip()

    # Parse JSON
    data = json.loads(response_text)

    if 'findings' not in data:
        raise KeyError("'findings' field not found in response.")

    return data['findings']

def extract_action_from_response_text(response_text: str) -> str:
    """
    Extracts the 'action' field from a JSON-formatted response string.

    Args:
        response_text (str): The raw response text from Gemini (may contain ```json ... ``` markers).

    Returns:
        str: The value of the 'action' field.

    Raises:
        KeyError: If 'action' field is missing.
        json.JSONDecodeError: If the text is not valid JSON.
    """
    # Clean if wrapped with ```json ... ```
    if response_text.strip().startswith('```json'):
        response_text = response_text.strip()[7:-3].strip()

    # Parse JSON
    data = json.loads(response_text)

    if 'action' not in data:
        raise KeyError("'action' field not found in response.")

    return data['action']

def get_response_from_gemini(prompt, image)-> Any:
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[image,prompt]
            )
            return response.text
        except genai.errors.ServerError as e:
            if "503" in str(e):
                print(f"Server overloaded (attempt {attempt + 1}), retrying in 20 seconds...")
                time.sleep(20)
            else:
                raise
    raise RuntimeError("Model still overloaded after retries.")
    return None


# Load variables from .env
load_dotenv()

# Read variables
api_key = os.getenv("GEMINI_API_KEY")
prompt = os.getenv("GEMINI_PROMPT")

# Constants
CSV_FILE_PATH = 'input/military_bases.csv'  # Path to the CSV file
ROWS_TO_PROCESS = 1                         # Number of rows to process
SCREENSHOTS_FOLDER = 'screen_shots'          # Folder to save screenshots

client = genai.Client(api_key=api_key)


# Read the CSV into a DataFrame
df = pd.read_csv(CSV_FILE_PATH)

# Set up Chrome browser options (we want the browser visible for debugging)
chrome_options = Options()

# Do NOT enable headless mode so we can see the browser
# chrome_options.add_argument('--headless')

# Create the Chrome driver (make sure you have chromedriver installed)
service = Service()  # You can specify chromedriver path here if needed
driver = webdriver.Chrome(service=service, options=chrome_options)

import os

# Define the folder
folder_path = "screen_shots"

# Check if folder exists, if not - create it
os.makedirs(folder_path, exist_ok=True)


# למשל לקרוא את הקובץ
# image = Image.open(screenshot_path)


# Loop over the first 5 rows
for idx, row in df.head(ROWS_TO_PROCESS).iterrows():
    camera_altitude_meters = 1000  # גובה המצלמה מעל הקרקע (meters)
    camera_tilt_degrees = 35  # זווית הטייה (degrees) מהאנך
    camera_heading_degrees = 0  # כיוון הצילום (0 = North)
    camera_time = 0  # זמן (לשימוש עתידי, כאן קבוע ל-0)
    camera_roll_degrees = 0  # סיבוב גלגול של המצלמה סביב עצמה
    latitude = row['latitude']  # Get latitude from the CSV row
    longitude = row['longitude']  # Get longitude from the CSV row
    last_analyz=""
    for attempt in range(8):


        # Build the Google Earth URL for the location
        url = (
            f"https://earth.google.com/web/@"
            f"{latitude},{longitude},"
            f"{camera_altitude_meters}a,"
            f"{camera_tilt_degrees}y,"
            f"{camera_heading_degrees}h,"
            f"{camera_time}t,"
            f"{camera_roll_degrees}r")

        print(f"Opening {url}")
        driver.get(url)

        # Wait for the page to fully load (otherwise screenshot might be blank)
        time.sleep(7)

        # Take a screenshot and save it
        screenshot_path = f"{SCREENSHOTS_FOLDER}/screenshot_{idx}_{attempt}.png"
        driver.save_screenshot(screenshot_path)
        print(f"Saved screenshot to {screenshot_path}")

        image = Image.open(screenshot_path).convert("RGB")
        if last_analyz=="":
            last_analyz_promt=""
        else:
            last_analyz_promt=f"Here is the analysis of previous analysts about this area and their recommendations. You can use this data but don’t use it as fact, think for yourself: {last_analyz}"
        response_text=get_response_from_gemini(prompt + last_analyz_promt,image)
        print(response_text)
        last_analyz=extract_findings_from_response_text(response_text)
        action = extract_action_from_response_text(response_text)
        if action == 'zoom-in':
            camera_altitude_meters = max(camera_altitude_meters - 100, 100)  # לא לרדת מתחת ל-100 מטר
        elif action == 'zoom-out':
            camera_altitude_meters += 100
        elif action == 'move-left':
            camera_heading_degrees = (camera_heading_degrees - 10) % 360  # להזיז 10 מעלות שמאלה
        elif action == 'move-right':
            camera_heading_degrees = (camera_heading_degrees + 10) % 360  # להזיז 10 מעלות ימינה
        elif action == 'finish':
            break
        else:
            print(f"Unknown action: {action}")

        #with open(f"output/output_{idx}.txt", "w") as f:
         #   f.write(response_text)

# Close the browser
driver.quit()
