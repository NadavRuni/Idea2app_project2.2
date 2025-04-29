from PIL import Image
from google import genai

client = genai.Client(api_key="AIzaSyBCrmSnWWdqqBmnLdjkdzuqsVaYJ18cdHs")

image = Image.open("screen_shots/screenshot_2.png").convert("RGB")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[image, "You are an expert in understanding satellite imagery and you work for the US army. We got intel that this area is a base/facility of the military of {country} . Analyze this image, try to find military devices, structures etc and tell me your findings "]
)
print(response.text)