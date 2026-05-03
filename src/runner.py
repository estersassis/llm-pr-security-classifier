from src.llm.llm_factory import LLMFactory
from src.llm.rich_api_log import log_llm_orchestration_attempt
from src.pr_formatter import PRFormatter
from src.utils import extract_json_from_response
import os
import json
import re
import time
import requests


class LLMRunner:
    def __init__(self, model, api_key, output_file_path="output.json", pr_folder_path="prs"):
        self.output_file_path = output_file_path
        self.pr_folder_path = pr_folder_path

        self.llm_handler = LLMFactory.get_processor(model, api_key)
        self.pr_formatter = PRFormatter()
        raw = self.load_existing_results()
        self.existing_results = self._normalize_to_flat(raw)

        processed_ids = {e["pr_id"] for e in self.existing_results if isinstance(e, dict) and e.get("pr_id")}
        for entry in raw:
            if isinstance(entry, dict) and "issues" in entry:
                pid = entry.get("id") or entry.get("context", {}).get("pr_id")
                if pid:
                    processed_ids.add(pid)
        self.processed_ids = processed_ids
    
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

    def _normalize_to_flat(self, data):
        """Converte para lista plana de issues [{pr_id, owasp_category, nature, summary, evidence?}, ...]."""
        if not isinstance(data, list):
            return []
        flat = []
        for entry in data:
            if isinstance(entry, dict) and "issues" in entry:
                pid = entry.get("id") or entry.get("context", {}).get("pr_id")
                for issue in entry.get("issues", []):
                    if isinstance(issue, dict):
                        i = dict(issue)
                        if not i.get("pr_id") and pid:
                            i["pr_id"] = pid
                        if i.get("pr_id"):
                            flat.append(i)
            elif isinstance(entry, dict) and entry.get("pr_id"):
                flat.append(entry)
        return flat

    def partial_save(self, results):
        with open(self.output_file_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"Progresso salvo com {len(results)} entradas.")
    
    def run(self, batch_size=15, max_batches=None, timeout=300):
        """
        Processamento em lote síncrono com tratamento de erros, retry e timeout.
        
        Args:
            batch_size: Número de PRs por batch
            max_batches: Limite de batches para testes (None = sem limite)
            timeout: Tempo máximo em segundos para cada requisição LLM (padrão: 300s)
        """
        start_time = time.time()
        print(f"Iniciando processamento em batch (batch_size={batch_size}, timeout={timeout}s)...")
        
        # Coletar arquivos para processar
        files_to_process = []
        skipped_count = 0
        
        for filename in os.listdir(self.pr_folder_path):
            if filename.endswith(".json"):
                pr_id = filename.replace(".json", "")
                if pr_id not in self.processed_ids:
                    files_to_process.append((os.path.join(self.pr_folder_path, filename), pr_id))
                else:
                    skipped_count += 1
        
        total_files = len(files_to_process)
        total_in_folder = total_files + skipped_count
        
        print(f"Total de arquivos na pasta: {total_in_folder}")
        print(f"Arquivos ja processados: {skipped_count}")
        print(f"Arquivos a processar: {total_files}")
        
        if total_files == 0:
            print("Nenhum arquivo novo para processar.")
            return
        
        # Limitar número de batches se especificado
        if max_batches:
            max_files = max_batches * batch_size
            if total_files > max_files:
                files_to_process = files_to_process[:max_files]
                print(f"Limitando processamento a {max_batches} batches ({max_files} arquivos)")
                total_files = max_files
        
        total_batches = (total_files + batch_size - 1) // batch_size
        print(f"Total de batches a processar: {total_batches}")
        print(f"{'-' * 60}")
        
        new_results_count = 0
        failed_batches = []
        batch_times = []
        
        for batch_num, i in enumerate(range(0, total_files, batch_size), 1):
            batch_start_time = time.time()
            chunk = files_to_process[i:i + batch_size]
            batch_payload = []
            batch_ids = []
            
            print(f"\n[Batch {batch_num}/{total_batches}] Processando {len(chunk)} PRs...")
            print(f"IDs: {[pr_id for _, pr_id in chunk]}")

            # Preparar payload do batch (estrutura: context, description, general_discussion, code_review_threads)
            format_errors = 0
            for file_path, pr_id in chunk:
                try:
                    data = self.pr_formatter.format_pr_discussions(file_path)
                    data["id"] = pr_id
                    if data.get("context"):
                        data["context"]["pr_id"] = pr_id
                    batch_payload.append(data)
                    batch_ids.append(pr_id)
                except Exception as e:
                    format_errors += 1
                    print(f"  ERRO formatacao {pr_id}: {str(e)[:100]}")
                    continue

            if format_errors > 0:
                print(f"  {format_errors} arquivo(s) com erro de formatacao")

            if not batch_payload:
                print(f"  Nenhum dado valido no batch. Pulando...")
                failed_batches.append((batch_num, "formatting_error"))
                continue

            # Tentar processar com retry
            raw_response = None
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    log_llm_orchestration_attempt(retry_count + 1, max_retries)
                    user_content = json.dumps(batch_payload, ensure_ascii=False)
                    raw_response = self.llm_handler.generate(user_content)
                    break

                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"  TIMEOUT apos {timeout}s. Tentativa {retry_count}/{max_retries}. Esperando 10 segundos...")
                        time.sleep(10)
                    else:
                        print(f"  TIMEOUT persistente apos {max_retries} tentativas. Pulando batch.")
                        failed_batches.append((batch_num, "timeout"))
                        break
                        
                except Exception as e:
                    error_msg = str(e)
                    retry_count += 1
                    
                    if "503" in error_msg:
                        if retry_count < max_retries:
                            print(f"  Servidor instavel (503). Tentativa {retry_count}/{max_retries}. Esperando 30 segundos...")
                            time.sleep(30)
                        else:
                            print(f"  Servidor instavel apos {max_retries} tentativas. Pulando batch.")
                            failed_batches.append((batch_num, "server_error"))
                            break
                            
                    elif "429" in error_msg:
                        print(f"  Requisicao rejeitada (429). Detalhes: {error_msg[:200]}...")
                        if retry_count < max_retries:
                            wait_match = re.search(r'retry in (\d+\.?\d*)', error_msg)
                            wait_time = float(wait_match.group(1)) if wait_match else 60
                            print(f"  Rate limit (429). Tentativa {retry_count}/{max_retries}. Esperando {wait_time:.1f}s...")
                            time.sleep(wait_time + 10)  # +10 segundos de margem
                        else:
                            print(f"  Rate limit persistente apos {max_retries} tentativas. Pulando batch.")
                            failed_batches.append((batch_num, "rate_limit"))
                            break
                    else:
                        print(f"  ERRO inesperado: {error_msg[:200]}")
                        failed_batches.append((batch_num, "unexpected_error"))
                        break
            
            if not raw_response:
                print(f"  Falha ao processar batch apos todas as tentativas.")
                continue
            
            # Extrair e salvar resultados
            print(f"  Extraindo resultados...")
            batch_results = extract_json_from_response(raw_response)

            # Normalizar: llm retorna lista [{pr_id, owasp_category, nature, summary, evidence?}, ...]
            if isinstance(batch_results, list):
                # Inicializa todos os PRs do batch (inclui PRs sem achados)
                by_pr = {pid: [] for pid in batch_ids}
                for item in batch_results:
                    if isinstance(item, dict) and "pr_id" in item:
                        pid = item["pr_id"]
                        by_pr.setdefault(pid, []).append(item)
                batch_results = by_pr
            elif not isinstance(batch_results, dict):
                batch_results = None

            if batch_results:
                new_issues = []
                if isinstance(batch_results, dict):
                    for pr_id, issues in batch_results.items():
                        if not isinstance(issues, list):
                            print(f"  AVISO: Issues para {pr_id} nao e uma lista, ignorando")
                            continue
                        self.processed_ids.add(pr_id)
                        if issues:
                            for issue in issues:
                                i = dict(issue) if isinstance(issue, dict) else {}
                                if not i.get("pr_id"):
                                    i["pr_id"] = pr_id
                                if i.get("pr_id"):
                                    new_issues.append(i)
                        else:
                            new_issues.append({
                                "pr_id": pr_id,
                                "owasp_category": "NONE",
                                "nature": "N/A",
                                "summary": "No security findings identified",
                                "evidence": "",
                            })
                else:
                    print(f"ERRO: Formato inesperado do resultado do batch. Esperado dict ou lista, recebido {type(batch_results)}. Conteudo: {str(batch_results)[:200]}")
                    continue

                self.existing_results.extend(new_issues)
                self.partial_save(self.existing_results)
                new_results_count += len(batch_results)
                
                batch_end_time = time.time()
                batch_duration = batch_end_time - batch_start_time
                batch_times.append(batch_duration)
                
                # Calcular tempo médio e estimativa
                avg_time = sum(batch_times) / len(batch_times)
                remaining_batches = total_batches - batch_num
                estimated_remaining = avg_time * remaining_batches
                
                print(f"  Batch concluido: {len(batch_results)} PRs salvos em {batch_duration:.1f}s")
                print(f"  Progresso: {new_results_count}/{total_files} arquivos ({(new_results_count/total_files)*100:.1f}%)")
                print(f"  Tempo medio por batch: {avg_time:.1f}s")
                print(f"  Tempo estimado restante: {estimated_remaining/60:.1f} minutos")
            else:
                print(f"  Nenhum resultado valido extraido do batch")
                failed_batches.append((batch_num, "extraction_failed"))
        
        # Sumário final
        total_time = time.time() - start_time
        print(f"\n{'-' * 60}")
        print(f"PROCESSAMENTO BATCH FINALIZADO")
        print(f"{'-' * 60}")
        print(f"Novos PRs processados: {new_results_count}/{total_files} ({(new_results_count/total_files)*100:.1f}%)")
        print(f"Batches concluidos: {len(batch_times)}/{total_batches}")
        print(f"Batches com falha: {len(failed_batches)}")
        if failed_batches:
            print(f"  Detalhes: {failed_batches}")
        print(f"Tempo total: {total_time/60:.2f} minutos")
        if batch_times:
            print(f"Tempo medio por batch: {sum(batch_times)/len(batch_times):.1f}s")
        print(f"{'-' * 60}")

    def execute_reprocess(self, pr_ids, batch_size=15, timeout=300):
        """
        Reprocessa PRs específicos por ID em modo batch.
        
        Args:
            pr_ids: Lista de IDs de PRs para reprocessar (ex: ["PR-123", "PR-456"])
            batch_size: Número de PRs por batch
            timeout: Tempo máximo em segundos para cada requisição LLM (padrão: 300s)
        """
        start_time = time.time()
        print(f"Iniciando reprocessamento de {len(pr_ids)} PRs...")
        print(f"IDs a reprocessar: {pr_ids}")
        print(f"Batch size: {batch_size}, Timeout: {timeout}s")
        print(f"{'-' * 60}")
        
        # Verificar quais arquivos existem
        files_to_process = []
        missing_ids = []
        
        for pr_id in pr_ids:
            filename = f"{pr_id}.json"
            file_path = os.path.join(self.pr_folder_path, filename)
            
            if os.path.exists(file_path):
                files_to_process.append((file_path, pr_id))
            else:
                missing_ids.append(pr_id)
        
        if missing_ids:
            print(f"AVISO: {len(missing_ids)} IDs nao encontrados na pasta:")
            print(f"  {missing_ids}")
        
        if not files_to_process:
            print("Nenhum arquivo encontrado para reprocessar.")
            return
        
        total_files = len(files_to_process)
        total_batches = (total_files + batch_size - 1) // batch_size
        print(f"Arquivos encontrados: {total_files}")
        print(f"Total de batches: {total_batches}")
        print(f"{'-' * 60}")
        
        reprocessed_results = {}
        failed_batches = []
        batch_times = []
        
        for batch_num, i in enumerate(range(0, total_files, batch_size), 1):
            batch_start_time = time.time()
            chunk = files_to_process[i:i + batch_size]
            batch_payload = []
            batch_ids = []
            
            print(f"\n[Batch {batch_num}/{total_batches}] Reprocessando {len(chunk)} PRs...")
            print(f"IDs: {[pr_id for _, pr_id in chunk]}")

            # Preparar payload do batch (estrutura: context, description, general_discussion, code_review_threads)
            format_errors = 0
            for file_path, pr_id in chunk:
                try:
                    data = self.pr_formatter.format_pr_discussions(file_path)
                    data["id"] = pr_id
                    if data.get("context"):
                        data["context"]["pr_id"] = pr_id
                    batch_payload.append(data)
                    batch_ids.append(pr_id)
                except Exception as e:
                    format_errors += 1
                    print(f"  ERRO formatacao {pr_id}: {str(e)[:100]}")
                    continue

            if format_errors > 0:
                print(f"  {format_errors} arquivo(s) com erro de formatacao")

            if not batch_payload:
                print(f"  Nenhum dado valido no batch. Pulando...")
                failed_batches.append((batch_num, "formatting_error"))
                continue

            # Tentar processar com retry
            raw_response = None
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    log_llm_orchestration_attempt(retry_count + 1, max_retries)
                    user_content = json.dumps(batch_payload, ensure_ascii=False)
                    raw_response = self.llm_handler.generate(user_content)
                    break

                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"  TIMEOUT apos {timeout}s. Tentativa {retry_count}/{max_retries}. Esperando 10 segundos...")
                        time.sleep(10)
                    else:
                        print(f"  TIMEOUT persistente apos {max_retries} tentativas. Pulando batch.")
                        failed_batches.append((batch_num, "timeout"))
                        break
                        
                except Exception as e:
                    error_msg = str(e)
                    retry_count += 1
                    
                    if "503" in error_msg:
                        if retry_count < max_retries:
                            print(f"  Servidor instavel (503). Tentativa {retry_count}/{max_retries}. Esperando 30 segundos...")
                            time.sleep(30)
                        else:
                            print(f"  Servidor instavel apos {max_retries} tentativas. Pulando batch.")
                            failed_batches.append((batch_num, "server_error"))
                            break
                            
                    elif "429" in error_msg:
                        print(f"  Requisicao rejeitada (429). Detalhes: {error_msg[:200]}...")
                        if retry_count < max_retries:
                            # Extrair tempo de espera da mensagem de erro
                            wait_match = re.search(r'retry in (\d+\.?\d*)', error_msg)
                            wait_time = float(wait_match.group(1)) if wait_match else 60
                            print(f"  Rate limit (429). Tentativa {retry_count}/{max_retries}. Esperando {wait_time:.1f}s...")
                            time.sleep(wait_time + 10)  # +10 segundos de margem
                        else:
                            print(f"  Rate limit persistente apos {max_retries} tentativas. Pulando batch.")
                            failed_batches.append((batch_num, "rate_limit"))
                            break
                    else:
                        print(f"  ERRO inesperado: {error_msg[:200]}")
                        failed_batches.append((batch_num, "unexpected_error"))
                        break
            
            if not raw_response:
                print(f"  Falha ao processar batch apos todas as tentativas.")
                continue
            
            # Extrair resultados
            print(f"  Extraindo resultados...")
            batch_results = extract_json_from_response(raw_response)

            # Normalizar: llm retorna lista [{pr_id, owasp_category, nature, summary, evidence?}, ...]
            if isinstance(batch_results, list):
                by_pr = {pid: [] for pid in batch_ids}
                for item in batch_results:
                    if isinstance(item, dict) and "pr_id" in item:
                        pid = item["pr_id"]
                        by_pr.setdefault(pid, []).append(item)
                batch_results = by_pr
            elif not isinstance(batch_results, dict):
                batch_results = None

            if batch_results and isinstance(batch_results, dict):
                for pr_id, issues in batch_results.items():
                    if not isinstance(issues, list):
                        print(f"  AVISO: Issues para {pr_id} nao e uma lista, ignorando")
                        continue
                    reprocessed_results[pr_id] = issues
                
                batch_end_time = time.time()
                batch_duration = batch_end_time - batch_start_time
                batch_times.append(batch_duration)
                
                # Calcular tempo médio e estimativa
                avg_time = sum(batch_times) / len(batch_times)
                remaining_batches = total_batches - batch_num
                estimated_remaining = avg_time * remaining_batches
                
                print(f"  Batch concluido: {len(batch_results)} PRs processados em {batch_duration:.1f}s")
                print(f"  Progresso: {len(reprocessed_results)}/{total_files} arquivos ({(len(reprocessed_results)/total_files)*100:.1f}%)")
                if remaining_batches > 0:
                    print(f"  Tempo medio por batch: {avg_time:.1f}s")
                    print(f"  Tempo estimado restante: {estimated_remaining/60:.1f} minutos")
            else:
                print(f"  Nenhum resultado valido extraido do batch")
                failed_batches.append((batch_num, "extraction_failed"))
        
        # Substituir resultados no arquivo de saída (formato plano: [{pr_id, owasp_category, ...}, ...])
        if reprocessed_results:
            print(f"\n{'-' * 60}")
            print(f"Substituindo resultados no arquivo de saida...")

            # Agrupar existentes por pr_id
            by_pr = {}
            for issue in self.existing_results:
                if isinstance(issue, dict) and issue.get("pr_id"):
                    pid = issue["pr_id"]
                    by_pr.setdefault(pid, []).append(issue)

            def _ensure_pr_id(issue, pid):
                i = dict(issue) if isinstance(issue, dict) else {}
                if not i.get("pr_id"):
                    i["pr_id"] = pid
                return i if i.get("pr_id") else None

            updated_count = 0
            added_count = 0
            for pr_id, issues in reprocessed_results.items():
                normalized = [_ensure_pr_id(issue, pr_id) for issue in (issues or [])]
                normalized = [i for i in normalized if i]
                if not normalized:
                    normalized = [{
                        "pr_id": pr_id,
                        "owasp_category": "NONE",
                        "nature": "N/A",
                        "summary": "No security findings identified",
                        "evidence": "",
                    }]
                if pr_id in by_pr:
                    by_pr[pr_id] = normalized
                    updated_count += 1
                else:
                    by_pr[pr_id] = normalized
                    added_count += 1

            # Achatar de volta para lista
            self.existing_results = [issue for issues in by_pr.values() for issue in issues]

            self.partial_save(self.existing_results)

            print(f"Resultados atualizados: {updated_count}")
            print(f"Novos resultados adicionados: {added_count}")
        
        # Sumário final
        total_time = time.time() - start_time
        print(f"\n{'-' * 60}")
        print(f"REPROCESSAMENTO FINALIZADO")
        print(f"{'-' * 60}")
        print(f"PRs reprocessados: {len(reprocessed_results)}/{total_files} ({(len(reprocessed_results)/total_files)*100:.1f}%)")
        print(f"Batches concluidos: {len(batch_times)}/{total_batches}")
        print(f"Batches com falha: {len(failed_batches)}")
        if failed_batches:
            print(f"  Detalhes: {failed_batches}")
        if missing_ids:
            print(f"IDs nao encontrados: {len(missing_ids)}")
        print(f"Tempo total: {total_time/60:.2f} minutos")
        if batch_times:
            print(f"Tempo medio por batch: {sum(batch_times)/len(batch_times):.1f}s")
        print(f"{'-' * 60}")
        
