"""Tests for CLI multi-format output support."""

from pathlib import Path

import pytest

from videocaptioner.cli.commands.transcribe import _resolve_output_paths
from videocaptioner.cli.main import build_parser
from videocaptioner.cli.validators import parse_output_formats


class TestParseOutputFormats:
    def test_single_format(self):
        assert parse_output_formats("srt") == ["srt"]

    def test_comma_separated(self):
        assert parse_output_formats("srt,txt") == ["srt", "txt"]

    def test_whitespace_and_case(self):
        assert parse_output_formats(" SRT , Json ") == ["srt", "json"]

    def test_sequence(self):
        assert parse_output_formats(["txt", "srt"]) == ["txt", "srt"]

    def test_deduplicates_preserving_order(self):
        assert parse_output_formats("srt,txt,srt") == ["srt", "txt"]

    def test_none_defaults_to_srt(self):
        assert parse_output_formats(None) == ["srt"]

    def test_rejects_unsupported(self):
        with pytest.raises(ValueError):
            parse_output_formats("srt,mp4")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            parse_output_formats(" , ")


class TestFormatArgument:
    def test_cli_accepts_multiple_formats(self):
        args = build_parser().parse_args(
            ["transcribe", "video.mp4", "--format", "srt,txt"]
        )
        assert args.format == ["srt", "txt"]

    def test_cli_rejects_unsupported_format(self):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(
                ["transcribe", "video.mp4", "--format", "srt,mp4"]
            )
        assert exc.value.code == 2


class TestResolveOutputPaths:
    def test_default_paths_per_format(self):
        paths = _resolve_output_paths(None, Path("/videos/demo.mp4"), ["srt", "txt"])
        assert paths == ["/videos/demo.srt", "/videos/demo.txt"]

    def test_directory_output(self, tmp_path):
        paths = _resolve_output_paths(str(tmp_path), Path("/videos/demo.mp4"), ["srt", "txt"])
        assert paths == [
            str(tmp_path / "demo.srt"),
            str(tmp_path / "demo.txt"),
        ]

    def test_named_file_gets_one_path_per_format(self, tmp_path):
        out = tmp_path / "custom.srt"
        paths = _resolve_output_paths(str(out), Path("/videos/demo.mp4"), ["srt", "txt"])
        assert paths == [str(tmp_path / "custom.srt"), str(tmp_path / "custom.txt")]

    def test_named_file_without_extension(self, tmp_path):
        out = tmp_path / "custom"
        paths = _resolve_output_paths(str(out), Path("/videos/demo.mp4"), ["srt", "txt"])
        assert paths == [str(tmp_path / "custom.srt"), str(tmp_path / "custom.txt")]

    def test_single_format_keeps_explicit_path(self, tmp_path):
        out = tmp_path / "custom.ass"
        paths = _resolve_output_paths(str(out), Path("/videos/demo.mp4"), ["srt"])
        assert paths == [str(out)]
