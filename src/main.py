import os
import json
import sys
import asyncio
import httpx
import time
from pr_formatter import PRFormatter
from llm_processor import LLMProcessor
from utils import extract_json_from_response

BASE_DIR = os.path.dirname(__file__)[:-4]
CONCURRENCY_LIMIT = 5
BATCH_SAVE_SIZE = 30

class LLMRunner:
    def __init__(self, model="gpt-4o", output_file_path="output.json", pr_folder_path="prs", api_key=None):
        self.output_file_path = output_file_path
        self.pr_folder_path = pr_folder_path

        self.llm_processor = LLMProcessor(model, api_key)
        self.pr_formatter = PRFormatter()
        self.existing_results = self.load_existing_results()

        processed_ids = [entry["id"] for entry in self.existing_results]
        self.processed_ids = set(processed_ids)

        self.save_lock = asyncio.Lock()
        
    def llm(self, pr_data):
        self.llm_processor.prompt_formatting(pr_data)
        return self.llm_processor.llm()
    
    def async_llm(self, client: httpx.AsyncClient, pr_data, file=None):
        self.llm_processor.prompt_formatting(pr_data, file)
        return self.llm_processor.async_llm(client)
    
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
        try:
            raw_response = self.llm(pr_data)
        except Exception as e:
            if "503" in str(e):
                print("Servidor instável. Esperando 30 segundos...")
                time.sleep(30)
                raw_response = self.llm(pr_data)
        json_response = extract_json_from_response(raw_response)
        if not json_response and json_response != []:
            print(f"Não foi possível extrair JSON válido da resposta LLM para {raw_response}.")

        json_response = {"id": id, "issues": json_response}

        return json_response, id

    async def process_pr_file_async(self, client: httpx.AsyncClient, file_path: str, filename: str, semaphore: asyncio.Semaphore):
        async with semaphore: # Adquire o semáforo (espera se estiver cheio)
            id = filename.replace(".json", "")
            if id in self.processed_ids:
                return None

            print(f"Processando {filename} (ID {id})...")
            try:
                pr_data = self.pr_formatter.format_pr_discussions(file_path)
            except Exception as e:
                print(f"Erro ao formatar {filename}: {e}")
                return None

            # Chama o LLM (que agora formata o prompt interno)
            raw_response = await self.async_llm(client, pr_data, filename)
            
            if not raw_response:
                print(f"Falha ao processar LLM para {id}. Resposta vazia.")
                return None

            json_response = extract_json_from_response(raw_response)
            if not json_response and json_response != []:
                print(f"Não foi possível extrair JSON válido da resposta LLM para {id}: {raw_response[:100]}...")
                json_response = {"error": "extraction_failed", "raw_response": raw_response}

            result_entry = {"id": id, "issues": json_response}
            return result_entry
    
    async def partial_save_async(self, new_results: list):
        if not new_results:
            return
            
        async with self.save_lock:
            current_data = self.load_existing_results()
            current_data.extend(new_results)
            
            with open(self.output_file_path, "w", encoding="utf-8") as f:
                json.dump(current_data, f, ensure_ascii=False, indent=4)
            
            print(f"💾 Progresso salvo. {len(new_results)} novos. Total: {len(current_data)}.")

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
    
    async def execute_async(self):
        """
        Método principal de execução assíncrona.
        """
        start_total_time = time.time()
        
        async with httpx.AsyncClient() as client:
            
            # 1. PREPARAR TAREFAS (Sem passo de aquecimento)
            files_to_process = []
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

            print("Escaneando arquivos para processar...")
            for filename in os.listdir(self.pr_folder_path):
                if not filename.endswith(".json"):
                    continue
                
                id = filename.replace(".json", "")
                if id in self.processed_ids:
                    continue
                
                file_path = os.path.join(self.pr_folder_path, filename)
                files_to_process.append((file_path, filename))

            total_files = len(files_to_process)
            print(f"Encontrados {total_files} novos arquivos para processar.")
            if total_files == 0:
                print("Nenhum arquivo novo. Encerrando.")
                return

            # 2. EXECUTAR EM LOTES
            new_results_count = 0
            
            for i in range(0, total_files, BATCH_SAVE_SIZE):
                batch_files = files_to_process[i:i + BATCH_SAVE_SIZE]
                
                print(f"\n--- Processando Lote {i // BATCH_SAVE_SIZE + 1} / {(total_files + BATCH_SAVE_SIZE - 1) // BATCH_SAVE_SIZE} ({len(batch_files)} arquivos) ---")
                
                tasks = [
                    self.process_pr_file_async(client, file_path, filename, semaphore)
                    for file_path, filename in batch_files
                ]
                
                start_batch_time = time.time()
                results = await asyncio.gather(*tasks)
                end_batch_time = time.time()
                
                valid_results = [r for r in results if r]
                new_results_count += len(valid_results)

                # Salva o progresso deste lote
                await self.partial_save_async(valid_results)
                
                # Atualiza o set de processados
                for r in valid_results:
                    self.processed_ids.add(r["id"])

                print(f"Lote concluído em {end_batch_time - start_batch_time:.2f} segundos.")
                
        end_total_time = time.time()
        print(f"\nProcessamento finalizado. {new_results_count} novos PRs processados.")
        print(f"Tempo total: {(end_total_time - start_total_time) / 60:.2f} minutos.")



runner = LLMRunner(
    model=sys.argv[2] if len(sys.argv) > 2 else "gemini-2.5-flash-lite",
    output_file_path=sys.argv[1] if len(sys.argv) > 1 else "output.json",
    pr_folder_path=os.path.join(BASE_DIR, "", "django"),
    api_key=os.getenv("GOOGLE_API_KEY")
)

if sys.argv[3] == "async":
    asyncio.run(runner.execute_async())
else:
    runner.execute()