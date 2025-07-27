# skynet_defense/api_module.py
import requests

class SubstackAPI:
    def __init__(self, api_key, base_url="https://api.substack.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    def connect(self):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(f"{self.base_url}/models", headers=headers)
            if response.status_code == 200:
                print("Substack API Connected")
                return response.json()
            else:
                print(f"Failed: {response.status_code}")
        except Exception as err:
            print(f"Error: {err}")

    def force_start_ai_model(self, model_id):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"action": "force_start", "model_id": model_id}
        try:
            response = requests.post(f"{self.base_url}/ai/start", json=payload, headers=headers)
            if response.status_code == 200:
                print(f"Started Model: {model_id}")
                return response.json()
            else:
                print(f"Failed: {response.status_code}")
        except Exception as err:
            print(f"Error: {err}")
