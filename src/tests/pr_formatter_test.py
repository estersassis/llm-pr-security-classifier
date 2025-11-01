import json
import pytest
import tempfile
import os
from unittest.mock import patch, mock_open
from ..pr_formatter import PRFormatter
from .pr_example import input_data, output_data


class TestPRFormatter:
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.formatter = PRFormatter()
        
    def test_open_pr_file_success(self):
        """Test successfully opening and parsing a PR JSON file."""
        # Create a temporary file with test data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(input_data, temp_file)
            temp_file_path = temp_file.name
        
        try:
            result = self.formatter._open_pr_file(temp_file_path)
            assert result == input_data
            assert result["title"] == "Fix override decorator"
            assert result["id"] == "MDExOlB1bGxSZXF1ZXN0MjA0NjQ2NTU="
        finally:
            os.unlink(temp_file_path)
    
    def test_open_pr_file_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.formatter._open_pr_file("non_existent_file.json")
    
    def test_open_pr_file_invalid_json(self):
        """Test handling of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write("invalid json content")
            temp_file_path = temp_file.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                self.formatter._open_pr_file(temp_file_path)
        finally:
            os.unlink(temp_file_path)
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_complete(self, mock_open_file):
        """Test complete PR formatting with all fields."""
        mock_open_file.return_value = input_data
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        # Verify structure
        assert "pr" in result
        assert "threads" in result
        
        # Verify PR section
        pr_section = result["pr"]
        assert pr_section["title"] == "Fix override decorator"
        assert pr_section["id"] == "MDExOlB1bGxSZXF1ZXN0MjA0NjQ2NTU="
        assert pr_section["description"] == "See https://code.djangoproject.com/ticket/23381#ticket\n"
        
        # Verify threads structure
        threads = result["threads"]
        assert len(threads) == 3
        
        # Verify PR-level thread (general discussion)
        pr_thread = threads[0]
        assert pr_thread["scope"] == "PR"
        assert len(pr_thread["discussion"]) == 4
        assert "I would find it useful to write two tests" in pr_thread["discussion"][0]
        
        # Verify file-specific threads
        file_threads = [t for t in threads if t["scope"].startswith("FILE:")]
        assert len(file_threads) == 2
        
        # Find timezone.py thread
        timezone_thread = next(t for t in file_threads if "timezone.py" in t["scope"])
        assert timezone_thread["scope"] == "FILE:django/utils/timezone.py"
        assert len(timezone_thread["discussion"]) == 2
        assert "Why not remove that line entirely?" in timezone_thread["discussion"][0]
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_minimal_data(self, mock_open_file):
        """Test formatting with minimal PR data."""
        minimal_data = {
            "title": "Simple PR",
            "body": "Simple description",
            "timeline_items": []
        }
        mock_open_file.return_value = minimal_data
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        assert result["pr"]["title"] == "Simple PR"
        assert result["pr"]["description"] == "Simple description"
        assert result["pr"]["id"] == ""  # Should default to empty string
        assert result["threads"] == []  # No timeline items, no threads
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_missing_fields(self, mock_open_file):
        """Test formatting when required fields are missing."""
        incomplete_data = {}
        mock_open_file.return_value = incomplete_data
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        # Should handle missing fields gracefully
        assert result["pr"]["title"] == ""
        assert result["pr"]["description"] == ""
        assert result["pr"]["id"] == ""
        assert result["threads"] == []
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_empty_comments(self, mock_open_file):
        """Test filtering out empty comments."""
        data_with_empty_comments = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {
                    "__typename": "IssueComment",
                    "body": ""  # Empty comment should be filtered out
                },
                {
                    "__typename": "IssueComment",
                    "body": "   "  # Whitespace-only comment should be filtered out
                },
                {
                    "__typename": "IssueComment",
                    "body": "Valid comment"
                }
            ]
        }
        mock_open_file.return_value = data_with_empty_comments
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        # Should only have one valid comment
        assert len(result["threads"]) == 1
        assert len(result["threads"][0]["discussion"]) == 1
        assert result["threads"][0]["discussion"][0] == "Valid comment"
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_line_comments(self, mock_open_file):
        """Test handling of line-specific comments."""
        data_with_line_comments = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "test.py",
                    "subject_type": "LINE",
                    "comments": [
                        {
                            "body": "Line comment",
                            "line": 42
                        }
                    ]
                }
            ]
        }
        mock_open_file.return_value = data_with_line_comments
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        # Should create LINE scope
        assert len(result["threads"]) == 1
        assert result["threads"][0]["scope"] == "LINE:test.py#L42"
        assert result["threads"][0]["discussion"][0] == "Line comment"
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_line_range_comments(self, mock_open_file):
        """Test handling of line range comments."""
        data_with_range_comments = {
            "title": "Test PR",
            "body": "Test description", 
            "timeline_items": [
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "test.py",
                    "subject_type": "LINE",
                    "comments": [
                        {
                            "body": "Range comment",
                            "start_line": 10,
                            "end_line": 15
                        }
                    ]
                }
            ]
        }
        mock_open_file.return_value = data_with_range_comments
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        # Should create LINE range scope
        assert len(result["threads"]) == 1
        assert result["threads"][0]["scope"] == "LINE:test.py#L10-L15"
        assert result["threads"][0]["discussion"][0] == "Range comment"
    
    @patch.object(PRFormatter, '_open_pr_file')
    def test_format_pr_discussions_unknown_subject_type(self, mock_open_file):
        """Test handling of unknown subject types."""
        data_with_unknown_type = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "test.py",
                    "subject_type": "UNKNOWN_TYPE",
                    "comments": [
                        {
                            "body": "Comment with unknown type"
                        }
                    ]
                }
            ]
        }
        mock_open_file.return_value = data_with_unknown_type
        
        result = self.formatter.format_pr_discussions("fake_path.json")
        
        # Should fallback to FILE scope
        assert len(result["threads"]) == 1
        assert result["threads"][0]["scope"] == "FILE:test.py"
        assert result["threads"][0]["discussion"][0] == "Comment with unknown type"
    
    def test_format_pr_discussions_with_real_file(self):
        """Integration test using a real temporary file."""
        # Create temporary file with input data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(input_data, temp_file)
            temp_file_path = temp_file.name
        
        try:
            result = self.formatter.format_pr_discussions(temp_file_path)
            
            # Should match expected output structure
            assert "pr" in result
            assert "threads" in result
            assert result["pr"]["title"] == output_data["pr"]["title"]
            assert len(result["threads"]) == len(output_data["threads"])
            
        finally:
            os.unlink(temp_file_path)