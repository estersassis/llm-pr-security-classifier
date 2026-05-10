from src.runner import LLMRunner
import os
from dotenv import load_dotenv
load_dotenv()

runner = LLMRunner(model="gemini-3.1-flash-lite", api_key=os.getenv("GEMINI_API_KEY"), output_file_path="django_gemini_3.1-flash-lite_0.json", pr_folder_path="django/prs")
runner.run(batch_size=20, max_batches=2000, timeout=300)