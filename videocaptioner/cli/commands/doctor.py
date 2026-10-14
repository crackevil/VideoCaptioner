"""doctor command -- diagnose local dependencies and configuration."""

import json
import shutil
import subprocess
import sys
from argparse import Namespace
from dataclasses import asdict, dataclass

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli.config import CONFIG_FILE, DEFAULTS, get


@dataclass
class Check:
    name: str
    status: str
    message: str
    fix: str = ""


def run(args: Namespace, config: dict) -> int:
    checks = _run_checks(config, check_api=bool(getattr(args, "check_api", False)))
    if getattr(args, "json", False):
        print(json.dumps({"checks": [asdict(c) for c in checks]}, ensure_ascii=False, indent=2))
    else:
        _print_checks(checks)
    return EXIT.DEPENDENCY_MISSING if any(c.status == "error" for c in checks) else EXIT.SUCCESS


def _run_checks(config: dict, *, check_api: bool = False) -> list[Check]:
    checks: list[Check] = []

    checks.append(_check_command("ffmpeg", "Required for audio extraction, timing fit, muxing, and hard subtitles."))
    checks.append(_check_command("ffprobe", "Required for media duration checks."))
    checks.append(_check_config_file())
    checks.extend(_check_transcribe(config))

    return checks



def _check_command(name: str, purpose: str) -> Check:
    path = shutil.which(name)
    if not path:
        return Check(name, "error", f"{name} not found. {purpose}", f"Install {name} and make sure it is on PATH")
    version = _command_version(name)
    return Check(name, "ok", f"{path}" + (f" ({version})" if version else ""))


def _command_version(name: str) -> str:
    try:
        result = subprocess.run([name, "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            return result.stdout.splitlines()[0][:100]
    except Exception:
        pass
    try:
        result = subprocess.run([name, "--version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout:
            return result.stdout.splitlines()[0][:100]
    except Exception:
        pass
    return ""


def _check_config_file() -> Check:
    if CONFIG_FILE.exists():
        return Check("config.file", "ok", str(CONFIG_FILE))
    return Check(
        "config.file",
        "warn",
        f"Config file does not exist: {CONFIG_FILE}",
        "Run 'videocaptioner config init' or set values with environment variables",
    )


def _check_transcribe(config: dict) -> list[Check]:
    asr = get(config, "transcribe.asr", "bijian")
    checks = [Check("transcribe.asr", "ok", f"default ASR: {asr}")]
    if asr == "whisper-cpp" and not any(shutil.which(n) for n in ["whisper-cpp", "whisper", "whisper-cpp-main"]):
        checks.append(Check("whisper-cpp", "error", "whisper.cpp binary not found", "Install whisper.cpp or choose --asr bijian"))
    return checks


def _print_checks(checks: list[Check]) -> None:
    for check in checks:
        prefix = {"ok": "OK", "warn": "WARN", "error": "ERROR"}.get(check.status, check.status.upper())
        print(f"{prefix:5} {check.name}: {check.message}")
        if check.fix:
            print(f"      fix: {check.fix}")
    errors = sum(1 for c in checks if c.status == "error")
    warnings = sum(1 for c in checks if c.status == "warn")
    if errors:
        print(f"ERROR Doctor found {errors} error(s) and {warnings} warning(s)")
    elif warnings:
        print(f"WARN  Doctor found {warnings} warning(s)")
    else:
        print("OK    Doctor found no issues")
