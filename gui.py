import streamlit as st
import json
import os
from PIL import Image

DATA_FILE = "data.json"
SCREENSHOT_FOLDER = "screen_shots"

# Load data
if not os.path.exists(DATA_FILE):
    st.error("No data.json file found.")
    st.stop()

with open(DATA_FILE, "r") as f:
    data = json.load(f)

st.set_page_config(page_title="Military Base Analyzer", layout="wide")
st.title("🛰️ Military Base Intelligence Report")
st.markdown("Showing all places analyzed by Gemini + DeepSeek.")

# Sidebar: filter by location
keys = list(data.keys())
selected_key = st.sidebar.selectbox("Select a Location", keys)

# Extract info
entry = data[selected_key]
latitude = entry["latitude"]
longitude = entry["longitude"]
gemini_findings = entry["findings"]
deepseek = entry["deepseek_summary"]

st.subheader(f"📍 Coordinates: {latitude}, {longitude}")
st.map(data={"lat": [latitude], "lon": [longitude]}, zoom=7)

# Screenshots
st.markdown("### 🖼️ Screenshots")
cols = st.columns(5)
for i in range(10):
    path = os.path.join(SCREENSHOT_FOLDER, f"screenshot_{keys.index(selected_key)}_{i}.png")
    if os.path.exists(path):
        with cols[i % 5]:
            st.image(Image.open(path), caption=f"Attempt {i}", use_container_width=True)

# Gemini Findings
st.markdown("### Gemini Findings (Raw Observations)")
for i, fset in enumerate(gemini_findings):
    st.markdown(f"**Observation {i + 1}:**")
    for point in fset:
        st.markdown(f"- {point}")

# DeepSeek Summary
st.markdown("### Commander Summary (DeepSeek Analysis)")

# Try parse JSON
if isinstance(deepseek, str):
    try:
        if deepseek.strip().startswith("```json"):
            deepseek = deepseek.strip()[7:-3].strip()
        deepseek = json.loads(deepseek)
    except Exception as e:
        st.error("Failed to parse DeepSeek summary")
        st.text(deepseek)
        st.stop()

st.markdown(f"- **Country:** {deepseek.get('country', 'N/A')}")
st.markdown(f"- **Army:** {deepseek.get('army', 'N/A')}")
st.markdown(f"- **Base Type:** {deepseek.get('base_type', 'N/A')}")

st.markdown("#### 🛣️ Access Routes")
for route in deepseek.get("access_routes", []):
    st.markdown(f"- {route}")

st.markdown("#### 💣 Special Weapons")
for weapon in deepseek.get("special_weapon", []):
    st.markdown(f"- {weapon}")

st.markdown("#### 🔍 Key Observations")
for obs in deepseek.get("key_observations", []):
    st.markdown(f"- {obs}")

st.markdown("#### 🎯 Recommended Attack Approaches")
for approach in deepseek.get("recommended_attack_routes", []):
    st.markdown(f"- {approach}")

st.markdown("#### 🧾 Conclusion")
st.success(deepseek.get("conclusion", "No conclusion provided."))
