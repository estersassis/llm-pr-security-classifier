import json
import pytest
import tempfile
import os
from unittest.mock import patch
from ..pr_formatter import PRFormatter
from .pr_example import input_data


class TestPRFormatter:
    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.formatter = PRFormatter()

    def test_open_pr_file_success(self):
        """Test successfully opening and parsing a PR JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
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
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            temp_file.write("invalid json content")
            temp_file_path = temp_file.name

        try:
            with pytest.raises(json.JSONDecodeError):
                self.formatter._open_pr_file(temp_file_path)
        finally:
            os.unlink(temp_file_path)

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_complete(self, mock_open_file):
        """Test complete PR formatting with all fields."""
        mock_open_file.return_value = input_data

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert set(result.keys()) == {
            "context",
            "description",
            "general_discussion",
            "code_review_threads",
        }

        ctx = result["context"]
        assert ctx["repository"] == "django/django"
        assert ctx["pr_number"] == 3135
        assert ctx["title"] == "Fix override decorator"
        assert ctx["state"] == "CLOSED"
        assert ctx["is_merged"] is False
        assert ctx["created_at"] == "2014-08-28T20:29:52.000Z"

        assert result["description"] == "See https://code.djangoproject.com/ticket/23381#ticket\n"

        gd = result["general_discussion"]
        assert len(gd) == 4
        assert "I would find it useful to write two tests" in gd[0]
        assert gd[0].endswith("respectively.")  # stripped trailing newline

        threads = result["code_review_threads"]
        assert len(threads) == 2

        timezone_thread = next(
            t for t in threads if "timezone.py" in t["scope"]
        )
        assert timezone_thread["scope"] == "FILE:django/utils/timezone.py"
        assert len(timezone_thread["comments"]) == 2
        assert "Why not remove that line entirely?" in timezone_thread["comments"][0]

        trans_thread = next(
            t for t in threads if "translation" in t["scope"]
        )
        assert trans_thread["scope"] == "FILE:django/utils/translation/__init__.py"
        assert trans_thread["comments"] == ["Same question as above."]

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_data_delegates_like_format_pr_discussions(self, mock_open_file):
        """format_pr_discussions loads file then format_pr_data."""
        mock_open_file.return_value = input_data
        from_file = self.formatter.format_pr_discussions("x.json")
        direct = self.formatter.format_pr_data(input_data)
        assert direct == from_file

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_minimal_data(self, mock_open_file):
        """Test formatting with minimal PR data."""
        minimal_data = {
            "title": "Simple PR",
            "body": "Simple description",
            "timeline_items": [],
        }
        mock_open_file.return_value = minimal_data

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert result["context"]["title"] == "Simple PR"
        assert result["context"]["repository"] == "unknown"
        assert result["context"]["pr_number"] is None
        assert result["description"] == "Simple description"
        assert result["general_discussion"] == []
        assert result["code_review_threads"] == []

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_missing_fields(self, mock_open_file):
        """Test formatting when required fields are missing."""
        mock_open_file.return_value = {}

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert result["context"]["title"] == ""
        assert result["context"]["repository"] == "unknown"
        assert result["context"]["pr_number"] is None
        assert result["description"] == ""
        assert result["general_discussion"] == []
        assert result["code_review_threads"] == []

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_empty_comments(self, mock_open_file):
        """Test filtering out empty IssueComment bodies."""
        data_with_empty_comments = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {"__typename": "IssueComment", "body": ""},
                {"__typename": "IssueComment", "body": "   "},
                {"__typename": "IssueComment", "body": "Valid comment"},
            ],
        }
        mock_open_file.return_value = data_with_empty_comments

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert result["general_discussion"] == ["Valid comment"]
        assert result["code_review_threads"] == []

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_line_comments(self, mock_open_file):
        """Review thread with line uses FILE:path#L{line}."""
        data_with_line_comments = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "test.py",
                    "comments": [
                        {"body": "Line comment", "line": 42},
                    ],
                }
            ],
        }
        mock_open_file.return_value = data_with_line_comments

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert len(result["code_review_threads"]) == 1
        t = result["code_review_threads"][0]
        assert t["scope"] == "FILE:test.py#L42"
        assert t["comments"] == ["Line comment"]

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_start_line_fallback(self, mock_open_file):
        """First comment start_line used when line is absent."""
        data_with_range_comments = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "test.py",
                    "comments": [
                        {
                            "body": "Range comment",
                            "start_line": 10,
                            "end_line": 15,
                        }
                    ],
                }
            ],
        }
        mock_open_file.return_value = data_with_range_comments

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert len(result["code_review_threads"]) == 1
        assert result["code_review_threads"][0]["scope"] == "FILE:test.py#L10"
        assert result["code_review_threads"][0]["comments"] == ["Range comment"]

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_thread_no_line(self, mock_open_file):
        """Review thread without line info: scope is FILE:path only."""
        data = {
            "title": "Test PR",
            "body": "Test description",
            "timeline_items": [
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "test.py",
                    "comments": [{"body": "File-level thread"}],
                }
            ],
        }
        mock_open_file.return_value = data

        result = self.formatter.format_pr_discussions("fake_path.json")

        assert result["code_review_threads"][0]["scope"] == "FILE:test.py"
        assert result["code_review_threads"][0]["comments"] == ["File-level thread"]

    @patch.object(PRFormatter, "_open_pr_file")
    def test_format_pr_discussions_skips_empty_review_thread(self, mock_open_file):
        """Thread with no comments or empty bodies is omitted."""
        mock_open_file.return_value = {
            "timeline_items": [
                {"__typename": "PullRequestReviewThread", "path": "a.py", "comments": []},
                {
                    "__typename": "PullRequestReviewThread",
                    "path": "b.py",
                    "comments": [{"body": ""}, {"body": "  "}],
                },
            ],
        }
        result = self.formatter.format_pr_discussions("fake_path.json")
        assert result["code_review_threads"] == []

    def test_format_pr_discussions_with_real_file(self):
        """Integration test using a real temporary file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
            json.dump(input_data, temp_file)
            temp_file_path = temp_file.name

        try:
            result = self.formatter.format_pr_discussions(temp_file_path)

            assert "context" in result
            assert "description" in result
            assert "general_discussion" in result
            assert "code_review_threads" in result
            assert result["context"]["title"] == "Fix override decorator"
            assert len(result["general_discussion"]) == 4
            assert len(result["code_review_threads"]) == 2
        finally:
            os.unlink(temp_file_path)
