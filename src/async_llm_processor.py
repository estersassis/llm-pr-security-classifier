import aiohttp
import asyncio
import json
from prompt import system_prompt


class AsyncLLMProcessor:
    def __init__(self, model, max_concurrent_requests=5):
        self.model = model
        self.system_prompt = system_prompt()
        self.prompt = None
        self.max_concurrent_requests = max_concurrent_requests
        
        self.url = "http://localhost:11434/api/generate"
        self.headers = {
            "Content-Type": "application/json",
        }
        
        # Create semaphore to limit concurrent requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300),  # 5 minute timeout
            connector=aiohttp.TCPConnector(limit=self.max_concurrent_requests)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def prompt_formatting(self, user):
        """Format the prompt with system and user content."""
        self.prompt = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user}
        ]

    async def llm(self, pr_data=None):
        """
        Async LLM request with rate limiting.
        
        Args:
            pr_data: If provided, will format prompt with this data
            
        Returns:
            str: LLM response text
        """
        if pr_data is not None:
            self.prompt_formatting(pr_data)
            
        if self.prompt is None:
            raise ValueError("O prompt deve ser definido antes de chamar llm()")

        data_llm = {
            "model": self.model,
            "prompt": str(self.prompt),
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        async with self.semaphore:  # Limit concurrent requests
            async with self.session.post(
                self.url, 
                headers=self.headers, 
                data=json.dumps(data_llm)
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    text = response_data.get('response', '').strip()
                    return text
                else:
                    error_text = await response.text()
                    raise Exception(f"LLM request failed with status code {response.status}: {error_text}")

    async def process_batch(self, pr_data_list):
        """
        Process multiple PR data items in parallel.
        
        Args:
            pr_data_list: List of PR data dictionaries
            
        Returns:
            List of LLM responses
        """
        tasks = []
        for pr_data in pr_data_list:
            # Create a new processor instance for each task to avoid prompt conflicts
            task = self._process_single_item(pr_data)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_single_item(self, pr_data):
        """Process a single PR data item."""
        try:
            # Format prompt for this specific item
            prompt = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": pr_data}
            ]
            
            data_llm = {
                "model": self.model,
                "prompt": str(prompt),
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            }

            async with self.semaphore:
                async with self.session.post(
                    self.url, 
                    headers=self.headers, 
                    data=json.dumps(data_llm)
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data.get('response', '').strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Requisição LLM falhou com código de status {response.status}: {error_text}")
        except Exception as e:
            return f"Error processing item: {str(e)}"
