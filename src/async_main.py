import os
import json
import sys
import asyncio
import aiofiles
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Tuple, Optional, Dict, Any
from pr_formatter import PRFormatter
from async_llm_processor import AsyncLLMProcessor
from utils import extract_json_from_response

BASE_DIR = os.path.dirname(__file__)[:-4]  


class OptimizedLLMRunner:
    def __init__(
        self, 
        model="gpt-4o", 
        output_file_path="output.json", 
        pr_folder_path="prs",
        max_concurrent_llm=5,
        max_concurrent_io=10,
        batch_size=20,
        save_interval=10
    ):
        self.output_file_path = output_file_path
        self.pr_folder_path = pr_folder_path
        self.max_concurrent_llm = max_concurrent_llm
        self.max_concurrent_io = max_concurrent_io
        self.batch_size = batch_size
        self.save_interval = save_interval
        
        self.model = model
        self.pr_formatter = PRFormatter()
        self.existing_results = None
        self.processed_ids = set()
        
        # Thread pool for CPU-bound operations (JSON parsing, formatting)
        self.thread_executor = ThreadPoolExecutor(max_workers=max_concurrent_io)
        
    async def initialize(self):
        """Initialize the runner and load existing results."""
        self.existing_results = await self.load_existing_results()
        processed_ids = [entry["id"] for entry in self.existing_results]
        self.processed_ids = set(processed_ids)
        
    async def load_existing_results(self) -> List[Dict]:
        """Async load existing results."""
        if os.path.exists(self.output_file_path):
            try:
                async with aiofiles.open(self.output_file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content) if content.strip() else []
            except (json.JSONDecodeError, Exception) as e:
                print(f"Arquivo JSON existente está corrompido ou incompleto: {e}")
                return []
        return []

    async def get_unprocessed_files(self) -> List[str]:
        """Get list of unprocessed JSON files."""
        files = []
        for filename in os.listdir(self.pr_folder_path):
            if filename.endswith(".json"):
                file_id = filename.replace(".json", "")
                if file_id not in self.processed_ids:
                    files.append(filename)
                else:
                    print(f"Pulando {filename} (ID já processado)")
        return files

    async def read_pr_file(self, filepath: str) -> Optional[Dict]:
        """Async read and parse PR file."""
        try:
            async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            print(f"Erro ao ler arquivo {filepath}: {e}")
            return None

    def format_pr_data_sync(self, raw_data: Dict) -> Dict:
        """Synchronous PR formatting (CPU-bound operation)."""
        return self.pr_formatter._format_pr_data(raw_data)

    async def process_file_batch(
        self, 
        filenames: List[str], 
        llm_processor: AsyncLLMProcessor
    ) -> List[Tuple[Optional[Dict], str]]:
        """Process a batch of files concurrently."""
        print(f"Processando lote de {len(filenames)} arquivos...")
        
        # Step 1: Read all files concurrently
        read_tasks = []
        for filename in filenames:
            filepath = os.path.join(self.pr_folder_path, filename)
            task = self.read_pr_file(filepath)
            read_tasks.append((task, filename))
        
        # Wait for all file reads to complete
        file_data = []
        for task, filename in read_tasks:
            raw_data = await task
            if raw_data:
                file_data.append((raw_data, filename))
        
        # Step 2: Format PR data in parallel using thread pool (CPU-bound)
        format_tasks = []
        loop = asyncio.get_event_loop()
        
        for raw_data, filename in file_data:
            task = loop.run_in_executor(
                self.thread_executor, 
                self.format_pr_data_sync, 
                raw_data
            )
            format_tasks.append((task, filename))
        
        formatted_data = []
        for task, filename in format_tasks:
            try:
                pr_data = await task
                formatted_data.append((pr_data, filename))
            except Exception as e:
                print(f"Erro ao formatar {filename}: {e}")
                continue
        
        # Step 3: Send all formatted data to LLM in parallel
        llm_tasks = []
        for pr_data, filename in formatted_data:
            task = llm_processor._process_single_item(pr_data)
            llm_tasks.append((task, filename, pr_data))
        
        # Wait for all LLM responses
        results = []
        for task, filename, pr_data in llm_tasks:
            try:
                raw_response = await task
                if isinstance(raw_response, Exception):
                    print(f"Erro do LLM para {filename}: {raw_response}")
                    results.append((None, filename.replace(".json", "")))
                else:
                    # Extract JSON from response
                    json_response = extract_json_from_response(raw_response)
                    if json_response:
                        result_entry = {
                            "id": filename.replace(".json", ""),
                            "issues": json_response
                        }
                        results.append((result_entry, filename.replace(".json", "")))
                    else:
                        print(f"Não foi possível extrair JSON válido da resposta LLM para {filename}: {raw_response}")
                        results.append((None, filename.replace(".json", "")))
            except Exception as e:
                print(f"Erro processando {filename}: {e}")
                results.append((None, filename.replace(".json", "")))
        
        return results

    async def save_results(self, results: List[Dict]):
        """Async save results to file."""
        try:
            async with aiofiles.open(self.output_file_path, "w", encoding="utf-8") as f:
                content = json.dumps(results, ensure_ascii=False, indent=4)
                await f.write(content)
            print(f"💾 Progresso salvo com {len(results)} entradas.")
        except Exception as e:
            print(f"Erro ao salvar resultados: {e}")

    async def execute_optimized(self):
        """Execute the optimized processing pipeline."""
        print("Iniciando processamento otimizado...")
        start_time = time.time()
        
        # Initialize
        await self.initialize()
        
        # Get unprocessed files
        unprocessed_files = await self.get_unprocessed_files()
        total_files = len(unprocessed_files)
        
        if total_files == 0:
            print("Nenhum arquivo novo para processar.")
            return
        
        print(f"Encontrados {total_files} arquivos para processar")
        
        new_results = []
        processed_count = 0
        
        # Create async LLM processor
        async with AsyncLLMProcessor(self.model, self.max_concurrent_llm) as llm_processor:
            
            # Process files in batches
            for i in range(0, total_files, self.batch_size):
                batch_files = unprocessed_files[i:i + self.batch_size]
                batch_start = time.time()
                
                # Process batch
                batch_results = await self.process_file_batch(batch_files, llm_processor)
                
                # Collect successful results
                for result_entry, file_id in batch_results:
                    if result_entry:
                        new_results.append(result_entry)
                        self.processed_ids.add(file_id)
                    processed_count += 1
                
                batch_time = time.time() - batch_start
                print(f"Batch {i//self.batch_size + 1} completado em {batch_time:.2f}s")
                print(f"Progresso: {processed_count}/{total_files} arquivos processados")
                
                # Save progress periodically
                if processed_count % self.save_interval == 0 or processed_count == total_files:
                    all_results = self.existing_results + new_results
                    await self.save_results(all_results)
        
        # Final save
        final_results = self.existing_results + new_results
        await self.save_results(final_results)
        
        total_time = time.time() - start_time
        print(f"Processamento otimizado concluído.")
        print(f"📊 Estatísticas:")
        print(f"   - Arquivos processados: {processed_count}")
        print(f"   - Novos resultados: {len(new_results)}")
        print(f"   - Tempo total: {total_time:.2f}s")
        print(f"   - Tempo médio por arquivo: {total_time/processed_count:.2f}s")
        print(f"   - Arquivos por segundo: {processed_count/total_time:.2f}")

    def __del__(self):
        """Cleanup thread executor."""
        if hasattr(self, 'thread_executor'):
            self.thread_executor.shutdown(wait=False)


class HybridLLMRunner(OptimizedLLMRunner):
    """
    Hybrid runner that can switch between sync and async processing
    based on available resources and file count.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sync_threshold = 50  # Switch to sync for small batches
        
    async def execute_hybrid(self):
        """Execute with adaptive sync/async strategy."""
        await self.initialize()
        unprocessed_files = await self.get_unprocessed_files()
        total_files = len(unprocessed_files)
        
        if total_files == 0:
            print("Nenhum arquivo novo para processar.")
            return
            
        if total_files < self.sync_threshold:
            print(f"Lote pequeno ({total_files} arquivos), usando processamento síncrono...")
            await self._execute_sync_optimized(unprocessed_files)
        else:
            print(f"Lote grande ({total_files} arquivos), usando processamento assíncrono...")
            await self.execute_optimized()
    
    async def _execute_sync_optimized(self, filenames: List[str]):
        """Optimized synchronous processing for small batches."""
        from llm_processor import LLMProcessor
        
        llm_processor = LLMProcessor(self.model)
        new_results = []
        
        for i, filename in enumerate(filenames, 1):
            filepath = os.path.join(self.pr_folder_path, filename)
            file_id = filename.replace(".json", "")
            
            try:
                print(f"Processando {filename} ({i}/{len(filenames)})...")
                
                # Read and format
                raw_data = await self.read_pr_file(filepath)
                if not raw_data:
                    continue
                    
                pr_data = self.format_pr_data_sync(raw_data)
                
                # LLM processing
                llm_processor.prompt_formatting(pr_data)
                raw_response = llm_processor.llm()
                
                # Extract JSON
                json_response = extract_json_from_response(raw_response)
                if json_response:
                    result_entry = {"id": file_id, "issues": json_response}
                    new_results.append(result_entry)
                    self.processed_ids.add(file_id)
                
            except Exception as e:
                print(f"Erro processando {filename}: {e}")
                continue
        
        # Save results
        final_results = self.existing_results + new_results
        await self.save_results(final_results)
        print(f"Processamento síncrono concluído. Novos resultados: {len(new_results)}")


async def main():
    """Main async entry point."""
    # Parse command line arguments
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:latest"
    output_file = sys.argv[1] if len(sys.argv) > 1 else "output.json"
    pr_folder = os.path.join(BASE_DIR, "", "django")
    
    # Create optimized runner
    runner = OptimizedLLMRunner(
        model=model,
        output_file_path=output_file,
        pr_folder_path=pr_folder,
        max_concurrent_llm=5,  # Adjust based on your server capacity
        max_concurrent_io=10,
        batch_size=20,  # Process 20 files per batch
        save_interval=20  # Save every 20 processed files
    )
    
    await runner.execute_optimized()


def run_hybrid():
    """Entry point for hybrid processing."""
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen3:latest"
    output_file = sys.argv[1] if len(sys.argv) > 1 else "output.json"
    pr_folder = os.path.join(BASE_DIR, "", "django")
    
    async def _run():
        runner = HybridLLMRunner(
            model=model,
            output_file_path=output_file,
            pr_folder_path=pr_folder,
            max_concurrent_llm=3,
            max_concurrent_io=8,
            batch_size=15,
            save_interval=15
        )
        await runner.execute_hybrid()
    
    asyncio.run(_run())


if __name__ == "__main__":
    # You can choose which runner to use:
    # asyncio.run(main())  # Pure async
    run_hybrid()  # Hybrid approach
