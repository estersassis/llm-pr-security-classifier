import os
import json
import sys
from pr_formatter import PRFormatter
from llm_processor import LLMProcessor
from utils import extract_json_from_response

BASE_DIR = os.path.dirname(__file__)[:-4]  

class LLMRunner:
    def __init__(self, model="gpt-4o", output_file_path="output.json", pr_folder_path="prs"):
        self.output_file_path = output_file_path
        self.pr_folder_path = pr_folder_path

        self.llm_processor = LLMProcessor(model)
        self.pr_formatter = PRFormatter()
        self.existing_results = self.load_existing_results()

        processed_ids = [entry["id"] for entry in self.existing_results]
        self.processed_ids = set(processed_ids)
        
    def llm(self, pr_data):
        self.llm_processor.prompt_formatting(pr_data)
        return self.llm_processor.llm()
    
    def load_existing_results(self):
        if os.path.exists(self.output_file_path):
            with open(self.output_file_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print("Arquivo JSON existente está corrompido ou incompleto.")
                    return []
        else:
            return []  

    def process_pr_file(self, file_path, filename):
        id = filename.replace(".json", "")
        if id in self.processed_ids:
            print(f"Pulando {file_path} (ID já processado)")
            return None, id

        print(f"Processando {filename} (ID {id})...")
        pr_data = self.pr_formatter.format_pr_discussions(file_path)
        raw_response = self.llm(pr_data)
        json_response = extract_json_from_response(raw_response)
        if not json_response:
            print(f"Não foi possível extrair JSON válido da resposta LLM para {raw_response}.")

        return json_response, id

    def partial_save(self, results):
        with open(self.output_file_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"💾 Progresso salvo com {len(results)} entradas.")

    def execute(self):
        new_results = []

        count = 0
        for filename in os.listdir(self.pr_folder_path):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(self.pr_folder_path, filename)
            result_entry, id = self.process_pr_file(file_path, filename)
            if result_entry:
                new_results.append(result_entry)
                self.processed_ids.add(id)
                count += 1
                print(f"Processados {count % 10}/10 arquivos")

            # Salva a cada bloco de N arquivos
            if count % 10 == 0 and count > 0:
                print(f"Processados 10 arquivos. Salvando...")
                self.partial_save(self.existing_results + new_results)

        self.partial_save(self.existing_results + new_results)
        print(f"Processamento finalizado. Total de novos PRs: {len(new_results)}")


runner = LLMRunner(
    model=sys.argv[2] if len(sys.argv) > 2 else "mistral:7b",
    output_file_path=sys.argv[1] if len(sys.argv) > 1 else "output.json",
    pr_folder_path=os.path.join(BASE_DIR, "", "django")
)

runner.execute()