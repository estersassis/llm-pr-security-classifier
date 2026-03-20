import json
import os
import pytest
import tempfile
from unittest.mock import Mock, patch, mock_open, MagicMock
from ..main import LLMRunner


class TestLLMRunner:
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.output_file = os.path.join(self.temp_dir, "test_output.json")
        self.pr_folder = os.path.join(self.temp_dir, "test_prs")
        os.makedirs(self.pr_folder, exist_ok=True)
        
        # Create a test runner instance
        self.runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        
        # Sample data for testing
        self.sample_pr_data = {
            "pr": {"title": "Test PR", "description": "Test description"},
            "threads": []
        }
        
        self.sample_llm_response = {
            "category": "Broken Access Control",
            "finding": "Missing authentication"
        }
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_init_default_values(self):
        """Test LLMRunner initialization with default values."""
        runner = LLMRunner()
        
        assert runner.output_file_path == "output.json"
        assert runner.pr_folder_path == "prs"
        assert runner.llm_processor is not None
        assert runner.pr_formatter is not None
        assert runner.processed_ids is not None
        assert runner.existing_results is not None
    
    def test_init_custom_values(self):
        """Test LLMRunner initialization with custom values."""
        runner = LLMRunner(
            model="custom-model",
            output_file_path="custom_output.json",
            pr_folder_path="custom_prs"
        )
        
        assert runner.output_file_path == "custom_output.json"
        assert runner.pr_folder_path == "custom_prs"
    
    @patch('src.main.LLMProcessor')
    def test_llm_method(self, mock_llm_processor_class):
        """Test llm method calls prompt_formatting and llm correctly."""
        # Setup mock
        mock_processor = Mock()
        mock_processor.llm.return_value = "mocked response"
        mock_llm_processor_class.return_value = mock_processor
        
        runner = LLMRunner()
        runner.llm_processor = mock_processor
        
        result = runner.llm(self.sample_pr_data)
        
        # Verify calls
        mock_processor.prompt_formatting.assert_called_once_with(self.sample_pr_data)
        mock_processor.llm.assert_called_once()
        assert result == "mocked response"
    
    def test_load_existing_results_no_file(self):
        """Test loading existing results when file doesn't exist."""
        runner = LLMRunner(output_file_path="nonexistent.json")
        
        assert runner.existing_results == []
        assert runner.processed_ids == set()
    
    def test_load_existing_results_valid_file(self):
        """Test loading existing results from valid JSON file."""
        existing_data = [
            {"id": "test1", "result": "data1"},
            {"id": "test2", "result": "data2"}
        ]
        
        # Create a temporary file with existing data
        with open(self.output_file, "w") as f:
            json.dump(existing_data, f)
        
        runner = LLMRunner(output_file_path=self.output_file)
        
        assert runner.existing_results == existing_data
        assert runner.processed_ids == {"test1", "test2"}
    
    def test_load_existing_results_corrupted_file(self):
        """Test loading existing results from corrupted JSON file."""
        # Create a corrupted JSON file
        with open(self.output_file, "w") as f:
            f.write("invalid json content")
        
        with patch('builtins.print') as mock_print:
            runner = LLMRunner(output_file_path=self.output_file)
            
            mock_print.assert_called_with("Arquivo JSON existente está corrompido ou incompleto.")
            assert runner.existing_results == []
            assert runner.processed_ids == set()
    
    @patch('src.main.extract_json_from_response')
    def test_process_pr_file_already_processed(self, mock_extract_json):
        """Test process_pr_file when PR is already processed."""
        self.runner.processed_ids = {"already_processed"}
        
        with patch('builtins.print') as mock_print:
            result = self.runner.process_pr_file("path/already_processed.json", "already_processed.json")
            
            mock_print.assert_called_with("Pulando path/already_processed.json (ID já processado)")
            assert result == (None, "already_processed")
            mock_extract_json.assert_not_called()
    
    @patch('src.main.extract_json_from_response')
    def test_process_pr_file_success(self, mock_extract_json):
        """Test successful processing of PR file."""
        mock_extract_json.return_value = self.sample_llm_response
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner, 'llm') as mock_llm:
                mock_format.return_value = self.sample_pr_data
                mock_llm.return_value = "raw llm response"
                
                with patch('builtins.print') as mock_print:
                    result = self.runner.process_pr_file("path/test.json", "test.json")
                    
                    mock_print.assert_called_with("Processando test.json (ID test)...")
                    mock_format.assert_called_once_with("path/test.json")
                    mock_llm.assert_called_once_with(self.sample_pr_data)
                    mock_extract_json.assert_called_once_with("raw llm response")
                    assert result == self.sample_llm_response
    
    @patch('src.main.extract_json_from_response')
    def test_process_pr_file_no_valid_json(self, mock_extract_json):
        """Test processing PR file when LLM response has no valid JSON."""
        mock_extract_json.return_value = None
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner, 'llm') as mock_llm:
                mock_format.return_value = self.sample_pr_data
                mock_llm.return_value = "invalid response"
                
                with patch('builtins.print') as mock_print:
                    result = self.runner.process_pr_file("path/test.json", "test.json")
                    
                    mock_print.assert_any_call("Processando test.json (ID test)...")
                    mock_print.assert_any_call("Não foi possível extrair JSON válido da resposta LLM para invalid response.")
                    assert result is None
    
    def test_partial_save(self):
        """Test partial save functionality."""
        test_results = [
            {"id": "test1", "result": "data1"},
            {"id": "test2", "result": "data2"}
        ]
        
        with patch('builtins.print') as mock_print:
            self.runner.partial_save(test_results)
            
            # Verify file was written
            assert os.path.exists(self.output_file)
            with open(self.output_file, "r") as f:
                saved_data = json.load(f)
            assert saved_data == test_results
            
            mock_print.assert_called_with("💾 Progresso salvo com 2 entradas.")
    
    @patch('os.listdir')
    def test_execute_no_json_files(self, mock_listdir):
        """Test execute when no JSON files exist."""
        mock_listdir.return_value = ["file1.txt", "file2.py"]
        
        with patch.object(self.runner, 'partial_save') as mock_save:
            with patch('builtins.print') as mock_print:
                self.runner.execute()
                
                mock_save.assert_called_once_with([])
                mock_print.assert_called_with("Processamento finalizado. Total de novos PRs: 0")
    
    @patch('os.listdir')
    def test_execute_with_json_files(self, mock_listdir):
        """Test execute with JSON files."""
        mock_listdir.return_value = ["test1.json", "test2.json", "ignore.txt"]
        
        # Mock process_pr_file to return different results
        def mock_process_side_effect(file_path, filename):
            if "test1" in filename:
                return {"id": "test1", "result": "result1"}, "test1"
            elif "test2" in filename:
                return {"id": "test2", "result": "result2"}, "test2"
            return None, None
        
        with patch.object(self.runner, 'process_pr_file', side_effect=mock_process_side_effect):
            with patch.object(self.runner, 'partial_save') as mock_save:
                with patch('builtins.print') as mock_print:
                    self.runner.execute()
                    
                    # Verify final save was called
                    assert mock_save.call_count >= 1
                    final_call_args = mock_save.call_args_list[-1][0][0]
                    assert len(final_call_args) == 2
                    
                    mock_print.assert_any_call("Processamento finalizado. Total de novos PRs: 2")
    
    @patch('os.listdir')
    def test_execute_with_periodic_save(self, mock_listdir):
        """Test execute with periodic saving every 10 files."""
        # Create 15 mock JSON files
        json_files = [f"test{i}.json" for i in range(15)]
        mock_listdir.return_value = json_files
        
        def mock_process_side_effect(file_path, filename):
            id_num = filename.replace("test", "").replace(".json", "")
            return {"id": f"test{id_num}", "result": f"result{id_num}"}, f"test{id_num}"
        
        with patch.object(self.runner, 'process_pr_file', side_effect=mock_process_side_effect):
            with patch.object(self.runner, 'partial_save') as mock_save:
                with patch('builtins.print') as mock_print:
                    self.runner.execute()
                    
                    # Should save at 10 files + final save
                    assert mock_save.call_count >= 2
                    mock_print.assert_any_call("Processados 10 arquivos. Salvando...")
                    mock_print.assert_any_call("Processamento finalizado. Total de novos PRs: 15")
    
    @patch('os.listdir')
    def test_execute_skip_already_processed(self, mock_listdir):
        """Test execute skips already processed files."""
        mock_listdir.return_value = ["test1.json", "test2.json"]
        self.runner.processed_ids = {"test1"}  # test1 already processed
        
        def mock_process_side_effect(file_path, filename):
            if "test1" in filename:
                return None, "test1"  # Already processed
            elif "test2" in filename:
                return {"id": "test2", "result": "result2"}, "test2"
            return None, None
        
        with patch.object(self.runner, 'process_pr_file', side_effect=mock_process_side_effect):
            with patch.object(self.runner, 'partial_save') as mock_save:
                with patch('builtins.print') as mock_print:
                    self.runner.execute()
                    
                    # Should only process test2
                    final_call_args = mock_save.call_args_list[-1][0][0]
                    new_results = [r for r in final_call_args if r.get("id") == "test2"]
                    assert len(new_results) == 1
                    
                    mock_print.assert_any_call("Processamento finalizado. Total de novos PRs: 1")
    
    def test_integration_with_real_files(self):
        """Integration test with real file operations."""
        # Create test JSON files
        test_pr_file = os.path.join(self.pr_folder, "integration_test.json")
        with open(test_pr_file, "w") as f:
            json.dump({"title": "Test PR", "body": "Test body", "timeline_items": []}, f)
        
        # Mock the LLM components
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner, 'llm') as mock_llm:
                with patch('src.main.extract_json_from_response') as mock_extract:
                    mock_format.return_value = self.sample_pr_data
                    mock_llm.return_value = "mocked llm response"
                    mock_extract.return_value = self.sample_llm_response
                    
                    self.runner.execute()
                    
                    # Verify output file was created
                    assert os.path.exists(self.output_file)
                    with open(self.output_file, "r") as f:
                        results = json.load(f)
                    
                    assert len(results) == 1
                    assert results[0] == self.sample_llm_response

    # ============================================
    # Tests for Batch Processing Functionality
    # ============================================
    
    @patch('os.listdir')
    def test_run_no_files(self, mock_listdir):
        """Test run when no files need processing."""
        mock_listdir.return_value = ["file1.txt", "file2.py"]
        
        with patch.object(self.runner, 'partial_save') as mock_save:
            self.runner.run(batch_size=15)
            
            # No files to process, so no saves should happen
            mock_save.assert_not_called()
    
    @patch('os.listdir')
    def test_run_single_batch(self, mock_listdir):
        """Test run with files fitting in single batch."""
        mock_listdir.return_value = ["test1.json", "test2.json", "test3.json"]
        
        # Mock batch processing response
        batch_response = {
            "test1": [{"category": "Injection", "issue": "SQL injection"}],
            "test2": [],
            "test3": [{"category": "XSS", "issue": "Cross-site scripting"}]
        }
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'prompt_formatting') as mock_prompt:
                with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                    with patch('src.main.extract_json_from_response') as mock_extract:
                        mock_format.return_value = self.sample_pr_data
                        mock_llm.return_value = "batch response"
                        mock_extract.return_value = batch_response
                        
                        with patch('builtins.print') as mock_print:
                            self.runner.run(batch_size=15)
                            
                            # Verify batch prompt was called
                            mock_prompt.assert_called_once()
                            args = mock_prompt.call_args[0][0]
                            assert isinstance(args, list)
                            assert len(args) == 3
                            
                            # Verify all IDs were processed
                            assert "test1" in self.runner.processed_ids
                            assert "test2" in self.runner.processed_ids
                            assert "test3" in self.runner.processed_ids
                            
                            mock_print.assert_any_call("Processando lote de 3 PRs...")
    
    @patch('os.listdir')
    def test_run_multiple_batches(self, mock_listdir):
        """Test run with files requiring multiple batches."""
        # Create 25 mock files (will need 2 batches of size 15)
        json_files = [f"test{i}.json" for i in range(25)]
        mock_listdir.return_value = json_files
        
        # Mock batch responses for each batch
        def mock_extract_side_effect(response):
            # Return different results for each batch call
            if mock_extract_side_effect.call_count <= 15:
                return {f"test{i}": [] for i in range(15)}
            else:
                return {f"test{i}": [] for i in range(15, 25)}
        
        mock_extract_side_effect.call_count = 0
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'prompt_formatting') as mock_prompt:
                with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                    with patch('src.main.extract_json_from_response') as mock_extract:
                        mock_format.return_value = self.sample_pr_data
                        mock_llm.return_value = "batch response"
                        
                        # Configure extract to return proper batch results
                        batch1_response = {f"test{i}": [] for i in range(15)}
                        batch2_response = {f"test{i}": [] for i in range(15, 25)}
                        mock_extract.side_effect = [batch1_response, batch2_response]
                        
                        with patch('builtins.print') as mock_print:
                            self.runner.run(batch_size=15)
                            
                            # Verify two batches were processed
                            assert mock_prompt.call_count == 2
                            assert mock_llm.call_count == 2
                            
                            mock_print.assert_any_call("Processando lote de 15 PRs...")
                            mock_print.assert_any_call("Processando lote de 10 PRs...")
    
    @patch('os.listdir')
    def test_run_skip_processed(self, mock_listdir):
        """Test run skips already processed files."""
        mock_listdir.return_value = ["test1.json", "test2.json", "test3.json"]
        self.runner.processed_ids = {"test1"}  # test1 already processed
        
        batch_response = {
            "test2": [{"category": "Injection", "issue": "SQL"}],
            "test3": []
        }
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'prompt_formatting') as mock_prompt:
                with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                    with patch('src.main.extract_json_from_response') as mock_extract:
                        mock_format.return_value = self.sample_pr_data
                        mock_llm.return_value = "batch response"
                        mock_extract.return_value = batch_response
                        
                        self.runner.run(batch_size=15)
                        
                        # Verify only 2 files were processed (test1 was skipped)
                        args = mock_prompt.call_args[0][0]
                        assert len(args) == 2
                        
                        # Verify test1 is still in processed but not re-added
                        assert "test1" in self.runner.processed_ids
                        assert "test2" in self.runner.processed_ids
                        assert "test3" in self.runner.processed_ids
    
    @patch('os.listdir')
    def test_run_with_issues(self, mock_listdir):
        """Test run correctly handles batch results with issues."""
        mock_listdir.return_value = ["test1.json", "test2.json"]
        
        batch_response = {
            "test1": [
                {"category": "Broken Access Control", "issue": "Missing auth check"},
                {"category": "Injection", "issue": "SQL injection risk"}
            ],
            "test2": [
                {"category": "Cryptographic Failures", "issue": "Weak hashing"}
            ]
        }
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'prompt_formatting') as mock_prompt:
                with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                    with patch('src.main.extract_json_from_response') as mock_extract:
                        with patch.object(self.runner, 'partial_save') as mock_save:
                            mock_format.return_value = self.sample_pr_data
                            mock_llm.return_value = "batch response"
                            mock_extract.return_value = batch_response
                            
                            self.runner.run(batch_size=15)
                            
                            # Verify save was called with correct data
                            mock_save.assert_called_once()
                            saved_data = mock_save.call_args[0][0]
                            
                            # Find the saved entries for test1 and test2
                            test1_entry = next(e for e in saved_data if e["id"] == "test1")
                            test2_entry = next(e for e in saved_data if e["id"] == "test2")
                            
                            assert len(test1_entry["issues"]) == 2
                            assert len(test2_entry["issues"]) == 1
                            assert test1_entry["issues"][0]["category"] == "Broken Access Control"
                            assert test2_entry["issues"][0]["category"] == "Cryptographic Failures"
    
    @patch('os.listdir')
    def test_run_empty_response(self, mock_listdir):
        """Test run handles empty/None response gracefully."""
        mock_listdir.return_value = ["test1.json", "test2.json"]
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'prompt_formatting') as mock_prompt:
                with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                    with patch('src.main.extract_json_from_response') as mock_extract:
                        with patch.object(self.runner, 'partial_save') as mock_save:
                            mock_format.return_value = self.sample_pr_data
                            mock_llm.return_value = "invalid response"
                            mock_extract.return_value = None  # Failed extraction
                            
                            self.runner.run(batch_size=15)
                            
                            # Should not crash, but also should not save anything
                            mock_save.assert_not_called()
    
    @patch('os.listdir')
    def test_run_custom_batch_size(self, mock_listdir):
        """Test run respects custom batch size."""
        json_files = [f"test{i}.json" for i in range(30)]
        mock_listdir.return_value = json_files
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'prompt_formatting') as mock_prompt:
                with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                    with patch('src.main.extract_json_from_response') as mock_extract:
                        mock_format.return_value = self.sample_pr_data
                        mock_llm.return_value = "batch response"
                        
                        # Each call returns a batch result
                        def create_batch_response(start, end):
                            return {f"test{i}": [] for i in range(start, end)}
                        
                        mock_extract.side_effect = [
                            create_batch_response(0, 10),
                            create_batch_response(10, 20),
                            create_batch_response(20, 30)
                        ]
                        
                        self.runner.run(batch_size=10)
                        
                        # Should process 3 batches of 10
                        assert mock_prompt.call_count == 3
                        
                        # Verify each batch had 10 items
                        for call in mock_prompt.call_args_list:
                            batch_data = call[0][0]
                            assert len(batch_data) == 10
    
    @patch('os.listdir')
    def test_run_integration(self, mock_listdir):
        """Integration test for batch processing with file I/O."""
        # Create test JSON files
        for i in range(3):
            test_file = os.path.join(self.pr_folder, f"batch_test{i}.json")
            with open(test_file, "w") as f:
                json.dump({
                    "title": f"Test PR {i}",
                    "body": f"Test body {i}",
                    "timeline_items": []
                }, f)
        
        mock_listdir.return_value = ["batch_test0.json", "batch_test1.json", "batch_test2.json"]
        
        batch_response = {
            "batch_test0": [{"category": "Injection", "issue": "Issue 0"}],
            "batch_test1": [],
            "batch_test2": [{"category": "XSS", "issue": "Issue 2"}]
        }
        
        with patch.object(self.runner.pr_formatter, 'format_pr_discussions') as mock_format:
            with patch.object(self.runner.llm_processor, 'llm') as mock_llm:
                with patch('src.main.extract_json_from_response') as mock_extract:
                    mock_format.return_value = self.sample_pr_data
                    mock_llm.return_value = "batch response"
                    mock_extract.return_value = batch_response
                    
                    self.runner.run(batch_size=15)
                    
                    # Verify output file was created with correct structure
                    assert os.path.exists(self.output_file)
                    with open(self.output_file, "r") as f:
                        results = json.load(f)
                    
                    assert len(results) == 3
                    
                    # Find specific results
                    result0 = next(r for r in results if r["id"] == "batch_test0")
                    result1 = next(r for r in results if r["id"] == "batch_test1")
                    result2 = next(r for r in results if r["id"] == "batch_test2")
                    
                    assert len(result0["issues"]) == 1
                    assert len(result1["issues"]) == 0
                    assert len(result2["issues"]) == 1



class TestLLMRunnerBatch:
    """Testes para a funcionalidade de processamento em batch."""

    def setup_method(self):
        """Configuração para cada teste."""
        import shutil
        self.temp_dir = tempfile.mkdtemp()
        self.output_file = os.path.join(self.temp_dir, "output.json")
        self.pr_folder = os.path.join(self.temp_dir, "prs")
        os.makedirs(self.pr_folder)
        self.shutil = shutil

    def teardown_method(self):
        """Limpeza após cada teste."""
        self.shutil.rmtree(self.temp_dir)

    def _create_test_pr_file(self, filename, content=None):
        """Helper para criar arquivo de PR de teste."""
        if content is None:
            content = {
                "title": f"Test PR {filename}",
                "description": "Test description",
                "threads": []
            }
        
        filepath = os.path.join(self.pr_folder, filename)
        with open(filepath, 'w') as f:
            json.dump(content, f)
        return filepath

    @patch('src.main.LLMProcessor')
    def test_run_basic(self, mock_processor_class):
        """Testa processamento básico em batch."""
        # Criar alguns arquivos de teste
        self._create_test_pr_file("pr1.json")
        self._create_test_pr_file("pr2.json")
        self._create_test_pr_file("pr3.json")

        # Mock do LLM processor
        mock_instance = MagicMock()
        mock_processor_class.return_value = mock_instance
        
        # Mock da resposta do LLM em batch (formato: {id: issues})
        mock_instance.llm.return_value = json.dumps({
            "pr1": [{"category": "Injection", "issue": "SQL injection found"}],
            "pr2": [],
            "pr3": [{"category": "Broken Access Control", "issue": "Auth bypass"}]
        })

        # Executar
        runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        runner.run(batch_size=3)

        # Verificações
        assert os.path.exists(self.output_file)
        
        with open(self.output_file, 'r') as f:
            results = json.load(f)
        
        assert len(results) == 3
        result_ids = [r["id"] for r in results]
        assert "pr1" in result_ids
        assert "pr2" in result_ids
        assert "pr3" in result_ids

    @patch('src.main.LLMProcessor')
    def test_run_with_multiple_batches(self, mock_processor_class):
        """Testa processamento em múltiplos batches."""
        # Criar 7 arquivos para testar com batch_size=3
        for i in range(1, 8):
            self._create_test_pr_file(f"pr{i}.json")

        mock_instance = MagicMock()
        mock_processor_class.return_value = mock_instance
        
        # Mock responderá com apenas os PRs do batch atual
        call_count = [0]
        def mock_llm_response(*args, **kwargs):
            call_count[0] += 1
            # Batch 1: pr1, pr2, pr3
            if call_count[0] == 1:
                return json.dumps({"pr1": [], "pr2": [], "pr3": []})
            # Batch 2: pr4, pr5, pr6
            elif call_count[0] == 2:
                return json.dumps({"pr4": [], "pr5": [], "pr6": []})
            # Batch 3: pr7
            else:
                return json.dumps({"pr7": []})
        
        mock_instance.llm.side_effect = mock_llm_response

        runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        runner.run(batch_size=3)

        # Verificar que foram chamados 3 batches (ceiling(7/3) = 3)
        assert mock_instance.llm.call_count == 3

        with open(self.output_file, 'r') as f:
            results = json.load(f)
        
        assert len(results) == 7
        result_ids = [r["id"] for r in results]
        for i in range(1, 8):
            assert f"pr{i}" in result_ids

    @patch('src.main.LLMProcessor')
    def test_run_skips_processed_ids(self, mock_processor_class):
        """Testa que o batch ignora IDs já processados."""
        # Criar arquivos
        self._create_test_pr_file("pr1.json")
        self._create_test_pr_file("pr2.json")
        self._create_test_pr_file("pr3.json")

        # Criar arquivo de output com pr1 já processado
        with open(self.output_file, 'w') as f:
            json.dump([{"id": "pr1", "issues": []}], f)

        mock_instance = MagicMock()
        mock_processor_class.return_value = mock_instance
        
        mock_instance.llm.return_value = json.dumps({
            "pr2": [],
            "pr3": []
        })

        runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        runner.run(batch_size=3)

        # Verificar que pr1 ainda está lá e pr2, pr3 foram adicionados
        with open(self.output_file, 'r') as f:
            results = json.load(f)
        
        ids = [r["id"] for r in results]
        assert "pr1" in ids
        assert "pr2" in ids
        assert "pr3" in ids

    @patch('src.main.LLMProcessor')
    def test_run_handles_llm_errors(self, mock_processor_class):
        """Testa tratamento de erros do LLM no modo batch."""
        self._create_test_pr_file("pr1.json")
        self._create_test_pr_file("pr2.json")

        mock_instance = MagicMock()
        mock_processor_class.return_value = mock_instance
        
        # Mock retorna resposta inválida
        mock_instance.llm.return_value = "Invalid JSON response"

        runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        
        # Não deve lançar exceção
        runner.run(batch_size=2)

    @patch('src.main.LLMProcessor')
    def test_run_preserves_existing_results(self, mock_processor_class):
        """Testa que resultados existentes são preservados."""
        # Criar resultados existentes
        existing_results = [
            {"id": "old_pr", "issues": [{"category": "Test", "issue": "Old issue"}]}
        ]
        with open(self.output_file, 'w') as f:
            json.dump(existing_results, f)

        # Criar novos arquivos
        self._create_test_pr_file("new_pr1.json")
        self._create_test_pr_file("new_pr2.json")

        mock_instance = MagicMock()
        mock_processor_class.return_value = mock_instance
        
        mock_instance.llm.return_value = json.dumps({
            "new_pr1": [],
            "new_pr2": [{"category": "Injection", "issue": "New issue"}]
        })

        runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        runner.run(batch_size=2)

        with open(self.output_file, 'r') as f:
            results = json.load(f)
        
        # Deve ter o antigo + os 2 novos
        assert len(results) == 3
        
        ids = [r["id"] for r in results]
        assert "old_pr" in ids
        assert "new_pr1" in ids
        assert "new_pr2" in ids

    @patch('src.main.LLMProcessor')
    def test_run_with_empty_folder(self, mock_processor_class):
        """Testa comportamento com pasta vazia."""
        mock_instance = MagicMock()
        mock_processor_class.return_value = mock_instance

        runner = LLMRunner(
            model="test-model",
            output_file_path=self.output_file,
            pr_folder_path=self.pr_folder
        )
        
        # Não deve lançar exceção
        runner.run(batch_size=3)
        
        # LLM não deve ser chamado
        mock_instance.llm.assert_not_called()