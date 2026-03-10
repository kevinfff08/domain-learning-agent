"""Tests for JSON repair utilities."""

import pytest

from src.utils.json_repair import repair_json, repair_json_array


class TestRepairJson:
    def test_valid_json(self):
        assert repair_json('{"a": 1}') == {"a": 1}

    def test_markdown_fences(self):
        raw = '```json\n{"a": 1}\n```'
        assert repair_json(raw) == {"a": 1}

    def test_trailing_comma(self):
        raw = '{"a": 1, "b": 2,}'
        assert repair_json(raw) == {"a": 1, "b": 2}

    def test_extra_text_around(self):
        raw = 'Here is the JSON:\n{"a": 1}\nDone.'
        assert repair_json(raw) == {"a": 1}

    def test_unclosed_brace(self):
        raw = '{"a": 1, "b": {"c": 2}'
        result = repair_json(raw)
        assert result["a"] == 1

    def test_nested_trailing_comma(self):
        raw = '{"nodes": [{"id": "a",}, {"id": "b",},]}'
        result = repair_json(raw)
        assert len(result["nodes"]) == 2

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            repair_json("no json here")

    def test_truncated_json(self):
        raw = '{"nodes": [{"id": "a"}, {"id": "b"'
        result = repair_json(raw)
        assert "nodes" in result


class TestRepairJsonArray:
    def test_valid_array(self):
        assert repair_json_array('[{"a": 1}]') == [{"a": 1}]

    def test_markdown_fences(self):
        raw = '```json\n[{"a": 1}]\n```'
        assert repair_json_array(raw) == [{"a": 1}]

    def test_trailing_comma(self):
        raw = '[{"a": 1}, {"b": 2},]'
        result = repair_json_array(raw)
        assert len(result) == 2

    def test_extra_text_around(self):
        raw = 'The result:\n[{"a": 1}]\nEnd.'
        assert repair_json_array(raw) == [{"a": 1}]

    def test_no_array_raises(self):
        with pytest.raises(ValueError, match="No JSON array found"):
            repair_json_array("no json here")

    def test_unclosed_bracket(self):
        raw = '[{"id": "a"}, {"id": "b"'
        result = repair_json_array(raw)
        assert len(result) >= 1
