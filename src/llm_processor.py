import requests
import json
from prompt import system_prompt


class LLMProcessor:
    def __init__(self, model):
        self.model = model
        self.system_prompt = system_prompt()
        self.prompt = None

        self.url = "http://localhost:11434/api/generate"
        self.headers = {
            "Content-Type": "application/json",
        }

    def prompt_formatting(self, user):
        self.prompt = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user}
        ]

    def llm(self):
        data_llm = {
            "model": self.model,
            "prompt": str(self.prompt),
            "stream": False,
            "options": {
                "temperature": 0.0
            }

        }

        response = requests.post(self.url, headers=self.headers, data=json.dumps(data_llm))
        if response.status_code == 200:
            response_data = response.json()
            text = response_data.get('response', '').strip()
            return text
        else:
            raise Exception(f"LLM request failed with status code {response.status_code}: {response.text}")