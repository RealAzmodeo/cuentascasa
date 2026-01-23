from google.generativeai import configure, list_models

API_KEY = "AIzaSyCSA0I0B_RTKbl-gL11xiNEnQ2vqIc4V1U"
configure(api_key=API_KEY)

print("Available models:")
for m in list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
