import json
from unittest.mock import Mock, patch

from src.runner import LLMRunner


def _write_pr_file(base_dir: str, pr_id: str, payload: dict) -> str:
    path = f"{base_dir}/{pr_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


def _base_formatted_pr(pr_id: str) -> dict:
    return {
        "context": {
            "repository": "repo/test",
            "pr_id": pr_id,
            "title": f"PR {pr_id}",
            "state": "open",
            "is_merged": False,
        },
        "description": "desc",
        "general_discussion": [],
        "code_review_threads": [],
    }


@patch("src.runner.LLMFactory.get_processor")
def test_runner_init_builds_processed_ids_from_id_and_context(mock_get_processor, tmp_path):
    mock_get_processor.return_value = Mock()
    output_file = tmp_path / "output.json"
    output_file.write_text(
        json.dumps(
            [
                {"id": "PR-1", "issues": []},
                {"context": {"pr_id": "PR-2"}, "issues": []},
            ]
        ),
        encoding="utf-8",
    )
    prs_dir = tmp_path / "prs"
    prs_dir.mkdir()

    runner = LLMRunner("gemini-test", "api-key", str(output_file), str(prs_dir))

    assert runner.processed_ids == {"PR-1", "PR-2"}


@patch("src.runner.LLMFactory.get_processor")
def test_run_saves_results_from_dict_response(mock_get_processor, tmp_path):
    handler = Mock()
    handler.generate.return_value = '{"PR-10": [{"owasp_category":"NONE"}]}'
    mock_get_processor.return_value = handler

    prs_dir = tmp_path / "prs"
    prs_dir.mkdir()
    _write_pr_file(
        str(prs_dir),
        "PR-10",
        {"id": "PR-10", "base_repository": "repo/test", "title": "x", "timeline_items": []},
    )
    output_file = tmp_path / "output.json"

    runner = LLMRunner("gemini-test", "api-key", str(output_file), str(prs_dir))
    with patch.object(runner.pr_formatter, "format_pr_discussions", return_value=_base_formatted_pr("PR-10")):
        runner.run(batch_size=10)

    saved = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["pr_id"] == "PR-10"
    assert saved[0]["owasp_category"] == "NONE"
    assert "PR-10" in runner.processed_ids
    assert handler.generate.call_count == 1


@patch("src.runner.LLMFactory.get_processor")
def test_run_normalizes_list_response_by_pr_id(mock_get_processor, tmp_path):
    handler = Mock()
    handler.generate.return_value = json.dumps(
        [
            {"pr_id": "PR-20", "owasp_category": "A05: Injection", "nature": "FIX/PREVENTION", "summary": "s1"},
            {"pr_id": "PR-20", "owasp_category": "NONE", "nature": "N/A", "summary": "s2"},
        ]
    )
    mock_get_processor.return_value = handler

    prs_dir = tmp_path / "prs"
    prs_dir.mkdir()
    _write_pr_file(
        str(prs_dir),
        "PR-20",
        {"id": "PR-20", "base_repository": "repo/test", "title": "x", "timeline_items": []},
    )
    output_file = tmp_path / "output.json"

    runner = LLMRunner("gemini-test", "api-key", str(output_file), str(prs_dir))
    with patch.object(runner.pr_formatter, "format_pr_discussions", return_value=_base_formatted_pr("PR-20")):
        runner.run(batch_size=10)

    saved = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(saved) == 2
    assert all(e["pr_id"] == "PR-20" for e in saved)
    assert saved[0]["owasp_category"] == "A05: Injection"
    assert saved[1]["owasp_category"] == "NONE"


@patch("src.runner.LLMFactory.get_processor")
def test_run_retries_on_timeout_and_eventually_succeeds(mock_get_processor, tmp_path):
    handler = Mock()
    handler.generate.side_effect = [
        TimeoutError("first timeout"),
        TimeoutError("second timeout"),
        '{"PR-30": []}',
    ]
    mock_get_processor.return_value = handler

    prs_dir = tmp_path / "prs"
    prs_dir.mkdir()
    _write_pr_file(
        str(prs_dir),
        "PR-30",
        {"id": "PR-30", "base_repository": "repo/test", "title": "x", "timeline_items": []},
    )
    output_file = tmp_path / "output.json"

    runner = LLMRunner("gemini-test", "api-key", str(output_file), str(prs_dir))
    with patch.object(runner.pr_formatter, "format_pr_discussions", return_value=_base_formatted_pr("PR-30")):
        with patch("src.runner.requests.exceptions.Timeout", TimeoutError):
            with patch("src.runner.time.sleep") as sleep_mock:
                runner.run(batch_size=10, timeout=1)

    saved = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(saved) == 1
    assert saved[0]["pr_id"] == "PR-30"
    assert saved[0]["owasp_category"] == "NONE"
    assert handler.generate.call_count == 3
    assert sleep_mock.call_count == 2


@patch("src.runner.LLMFactory.get_processor")
def test_execute_reprocess_updates_existing_entries(mock_get_processor, tmp_path):
    handler = Mock()
    handler.generate.return_value = '{"PR-40": [{"owasp_category":"A01: Broken Access Control"}]}'
    mock_get_processor.return_value = handler

    output_file = tmp_path / "output.json"
    output_file.write_text(
        json.dumps(
            [
                {"pr_id": "PR-40", "owasp_category": "NONE", "nature": "N/A", "summary": "x", "evidence": ""},
                {"pr_id": "PR-41", "owasp_category": "A05: Injection", "nature": "N/A", "summary": "y", "evidence": ""},
            ]
        ),
        encoding="utf-8",
    )

    prs_dir = tmp_path / "prs"
    prs_dir.mkdir()
    _write_pr_file(
        str(prs_dir),
        "PR-40",
        {"id": "PR-40", "base_repository": "repo/test", "title": "x", "timeline_items": []},
    )

    runner = LLMRunner("gemini-test", "api-key", str(output_file), str(prs_dir))
    with patch.object(runner.pr_formatter, "format_pr_discussions", return_value=_base_formatted_pr("PR-40")):
        runner.execute_reprocess(["PR-40"], batch_size=10)

    saved = json.loads(output_file.read_text(encoding="utf-8"))
    pr40 = [e for e in saved if e["pr_id"] == "PR-40"]
    pr41 = [e for e in saved if e["pr_id"] == "PR-41"]
    assert len(pr40) == 1
    assert pr40[0]["owasp_category"] == "A01: Broken Access Control"
    assert len(pr41) == 1
    assert pr41[0]["owasp_category"] == "A05: Injection"
