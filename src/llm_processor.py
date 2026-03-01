import requests
import json
import httpx
import time
from prompt import system_prompt


class LLMProcessor:
    def __init__(self, model, api_key=None):
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt()
        self.prompt = None
        self.file = None

        # Define se usaremos Gemini ou Ollama (localhost)
        if "gemini" in model.lower():
            self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        else:
            self.url = "http://localhost:11434/api/generate"
        self.headers = {
            "Content-Type": "application/json",
        }

    def prompt_formatting(self, user, file=None):
        self.file = file
        if "gemini" in self.model.lower():
            self.prompt = [
                {"role": "user", "parts": [{"text": f"System Instruction: {self.system_prompt}\n\nUser: {user}"}]}
            ]
        else:
            # Mantém seu formato original para o Ollama
            self.prompt = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user}
            ]
    
    async def async_llm(self, client: httpx.AsyncClient):
        data_llm = {
            "model": self.model,
            "prompt": str(self.prompt),
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        try:
            start_time = time.time()
            response = await client.post(self.url, headers=self.headers, data=json.dumps(data_llm), timeout=180.0)
            end_time = time.time()
            final_time = (end_time - start_time)
            print(f"{self.file} LLM request completed in {final_time}s.")
            if response.status_code == 200:
                response_data = response.json()
                text = response_data.get('response', '').strip()
                return text
            else:
                print(f"LLM request falhou: {response.status_code} {response.text}")
                return None
                
        except httpx.ReadTimeout:
            print(f"Erro: Timeout (LLM demorou mais de 180s para a requisição)")
            return None
        except Exception as e:
            print(f"Erro inesperado na requisição: {e}")
            return None

    def llm(self):
        if "gemini" in self.model.lower():
            # Estrutura de dados específica para Gemini
            data_llm = {
                "contents": self.prompt,
                "generationConfig": {
                    "temperature": 0.0
                }
            }
        else:
            # Estrutura de dados original (Ollama)
            data_llm = {
                "model": self.model,
                "prompt": str(self.prompt),
                "stream": False,
                "options": {"temperature": 0.0}
            }

        response = requests.post(self.url, headers=self.headers, data=json.dumps(data_llm))
        if response.status_code == 200:
            response_data = response.json()

            if "gemini" in self.model.lower():
                return response_data['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                return response_data.get('response', '').strip()
        else:
            raise Exception(f"LLM request failed with status code {response.status_code}: {response.text}")