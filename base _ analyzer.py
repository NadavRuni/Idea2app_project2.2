from typing import Any

import pandas as pd
from google import genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from PIL import Image
from dotenv import load_dotenv
import os
import json
import json
from typing import List
import requests
from typing import List


DATA_FILE = "data.json"

def load_existing_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_place_already_analyzed(data, latitude, longitude):
    key = f"{latitude},{longitude}"
    return key in data

def add_analysis_to_data(data, latitude, longitude, analysis_result):
    key = f"{latitude},{longitude}"
    data[key] = analysis_result
    save_data(data)

import json
import re

def clean_json_block(text: str) -> dict:
    """
    Cleans ```json ... ``` wrappers and parses the text into a real JSON object.
    Also tries to fix common issues like unclosed strings, misplaced confidence notes, etc.
    """
    if not text or text.strip() == "":
        raise ValueError("Empty response text received from model.")

    # Remove code block wrapper
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]

    # Strip again just in case
    text = text.strip()

    # Remove known patterns like "(90% confidence)"
    text = re.sub(r"\(\d+% confidence.*?\)", "", text)
    text = re.sub(r"\(low confidence.*?\)", "", text)

    # Try parsing directly
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print("❌ JSON decoding failed. Raw text:\n", text)
        print("Error:", e)

        # Try to recover: Truncate at last complete curly bracket
        last_close = text.rfind("}")
        if last_close != -1:
            try:
                return json.loads(text[:last_close+1])
            except Exception as e2:
                print("Second attempt failed:", e2)

        # Final fallback: Raise with original text shown
        raise ValueError(f"Failed to parse JSON. Raw text:\n{text}") from e


def upgraded_send_analyses_to_deepseek(api_key: str, analyzes: List[str], latitude: str, longitude: str) -> str:
    """
    Sends a list of analysis texts to deepseek/deepseek-r1 via OpenRouter and returns the model's response.
    Adds validation and debug printing if response is empty or malformed.
    """
    history_text = "\n".join([f"- {analysis}" for analysis in analyzes])
    prompt = (
        "You are a commander of military analysts investigating a possible enemy military site, based on the following analysts' reports:\n\n"
        f"{history_text}\n\n"
        f"The coordinates of the site are: {latitude},{longitude}\n\n"
        "Please analyze and return your findings STRICTLY in a JSON format with the following fields:\n"
        "1. country: (string, the country where the site is located)\n"
        "2. army: (string, the military organization operating the site)\n"
        "3. base_type: (string, one of: 'training', 'offensive', or 'mixed')\n"
        "4. access_routes: (list of strings, key roads, railways, or paths leading to the site include dirction and the road type)\n"
        "5. special_weapons: (list of strings, any special weapons or notable military equipment spotted)\n"
        "6. key_observations: (list of strings, each describing specific infrastructure, logistics, personnel, defense, or communications details)\n"
        "7. conclusion: (string, a short final summary of the site's purpose and strategic importance)\n"
        "8. threat_level: (string, overall threat level posed by this site — e.g., 'low', 'medium', 'high')\n"
        "9. recommended_attack_routes: (list of strings, suggested directions or methods of attack, based on geography and layout , very detailed plan at least 5 sentences)\n\n"
        "**Important:**\n"
        "- Respond ONLY with a valid JSON object.\n"
        "- Do NOT add any explanations, headers, or commentary outside the JSON.\n"
        "- Keep all field names and formatting EXACTLY as specified.\n"
        "- If you are unsure about any field, write \"unknown\" or an empty list where appropriate."
    )

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

        response.raise_for_status()
        result = response.json()

        # Try to get content safely
        content = result.get('choices', [{}])[0].get('message', {}).get('content', "").strip()

        if not content:
            print("❌ DeepSeek returned an empty or blank response.")
            print("📦 Full response JSON:")
            print(json.dumps(result, indent=2))
            raise ValueError("Empty response text received from DeepSeek.")

        return content

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"HTTP request to DeepSeek failed: {str(e)}")

    except Exception as e:
        raise RuntimeError(f"Unexpected error while calling DeepSeek: {str(e)}")
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
    for attempt in range(5):
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
def get_response_from_gemini_only_text(latitude,longitude)-> Any:
    for attempt in range(5):
        try:
            prompt = "I am providing you with the coordinates of a military base below.\nPlease return the following information in this exact format and do not include any other text:\n\nCountry:\nArmy Name:\nNearby Cities:\nBase Type (e.g., Navy, Air Force, Infantry...):\nCoordinates:\n"
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt,f"the cordinates of the site are: {latitude},{longitude}"]
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
api_key_gemini = os.getenv("GEMINI_API_KEY")
api_open_routher = os.getenv("OPEN_ROUTHER_API_KEY")
prompt = os.getenv("GEMINI_PROMPT")

# Constants
CSV_FILE_PATH = 'input/military_bases.csv'  # Path to the CSV file
ROWS_TO_PROCESS = 12                        # Number of rows to process
SCREENSHOTS_FOLDER = 'screen_shots'          # Folder to save screenshots

client = genai.Client(api_key=api_key_gemini)


# Read the CSV into a DataFrame
df = pd.read_csv(CSV_FILE_PATH)

# Set up Chrome browser options (we want the browser visible for debugging)
chrome_options = Options()

# Do NOT enable headless mode so we can see the browser
chrome_options.add_argument('--headless')

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
    existing_data = load_existing_data()
    key = f"{latitude},{longitude}"
    if key in existing_data:
        print(f"Already analyzed {latitude},{longitude}, skipping...")
        continue

    last_analyz=""
    findings=[]
    country_data="this is the base details :\n" +get_response_from_gemini_only_text(latitude,longitude)
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
            last_analyz_promt=f"\nHere is the analysis of previous analysts about this area and their recommendations. You can use this data but don’t use it as fact, think for yourself: {last_analyz}"
        response_text=get_response_from_gemini(country_data +"\n"+prompt + last_analyz_promt,image)
        print(response_text)
        last_analyz=extract_findings_from_response_text(response_text)
        findings.append(last_analyz)
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
    # שלח את כל הניתוחים ל-Deepseek
    deepseek_response_raw = upgraded_send_analyses_to_deepseek(api_open_routher, findings ,latitude,longitude)
    deepseek_response = clean_json_block(deepseek_response_raw)
    print(deepseek_response)

    # טען את קובץ הנתונים הקיים
    existing_data = load_existing_data()

    # בדוק אם כבר ניתחו את המקום
    key = f"{latitude},{longitude}"
    if key not in existing_data:
        # הוסף את הניתוח החדש
        existing_data[key] = {
            "latitude": latitude,
            "longitude": longitude,
            "findings": findings,
            "deepseek_summary": deepseek_response
        }
        # שמור הכל חזרה ל-data.json
        save_data(existing_data)
        print(f"Saved analysis for {latitude},{longitude}")
    else:
        print(f"Already analyzed {latitude},{longitude}, skipping save.")

        #with open(f"output/output_{idx}.txt", "w") as f:
        #   f.write(response_text)

# Close the browser
driver.quit()
