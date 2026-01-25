from app import app
import json

def test_summary():
    with app.test_client() as client:
        response = client.get('/summary')
        data = response.get_json()
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    test_summary()
