from src.runner import LLMRunner
import os
from dotenv import load_dotenv
load_dotenv()

runner = LLMRunner(model="gemini-2.5-flash-lite", api_key=os.getenv("GEMINI_API_KEY"), output_file_path="pilot.json", pr_folder_path="django")
runner.run(batch_size=10, max_batches=10, timeout=300)