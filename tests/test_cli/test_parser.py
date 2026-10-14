"""Tests for CLI argument parsing — verify all commands parse correctly."""

from argparse import Namespace

import pytest

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.commands.process import _resolve_final_output_path
from videocaptioner.cli.main import main


class TestTranscribeParser:
    def test_missing_input(self):
        with pytest.raises(SystemExit) as exc:
            main(["transcribe"])
        assert exc.value.code == 2

    def test_invalid_asr(self):
        with pytest.raises(SystemExit) as exc:
            main(["transcribe", "test.mp4", "--asr", "invalid"])
        assert exc.value.code == 2

    def test_file_not_found(self):
        assert main(["transcribe", "/nonexistent/file.mp4"]) == EXIT.FILE_NOT_FOUND

    def test_verbose_quiet_mutually_exclusive(self):
        with pytest.raises(SystemExit) as exc:
            main(["transcribe", "test.mp4", "-v", "-q"])
        assert exc.value.code == 2



class TestDoctorParser:
    def test_doctor_json(self, capsys):
        result = main(["doctor", "--json"])
        assert result in {EXIT.SUCCESS, EXIT.DEPENDENCY_MISSING}
        out = capsys.readouterr().out
        assert '"checks"' in out

    def test_doctor_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["doctor", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "--json" in out
        assert "--check-api" in out
