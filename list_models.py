from google import genai

API_KEY = "AIzaSyCSA0I0B_RTKbl-gL11xiNEnQ2vqIc4V1U"
client = genai.Client(api_key=API_KEY)

print("Available models:")
for m in client.models.list():
    print(m.name)
