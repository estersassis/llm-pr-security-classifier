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