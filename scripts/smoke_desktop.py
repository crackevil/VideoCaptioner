#!/usr/bin/env python3
"""Run real packaged-app smoke tests against a desktop bundle."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
from pathlib import Path


def _run(cmd: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    print("+ " + " ".join(str(part) for part in cmd))
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=True, text=True)


def _find_executable(bundle: Path) -> Path:
    if bundle.is_file():
        return bundle
    candidates = []
    if platform.system() == "Windows":
        candidates.append(bundle / "VideoCaptioner.exe")
    else:
        candidates.append(bundle / "VideoCaptioner")
        candidates.append(bundle / "VideoCaptioner.app" / "Contents" / "MacOS" / "VideoCaptioner")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"VideoCaptioner executable not found under {bundle}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Path to dist/VideoCaptioner or an executable")
    args = parser.parse_args()

    bundle = Path(args.bundle).resolve()
    exe = _find_executable(bundle)

    env = os.environ.copy()
    env["PATH"] = os.defpath
    env["VIDEOCAPTIONER_LLM_API_KEY"] = ""
    env["VIDEOCAPTIONER_TTS_API_KEY"] = ""

    _run([str(exe), "--version"], env=env)
    _run([str(exe), "style"], env=env)
    _run([str(exe), "doctor", "--json"], env=env)
    _run([str(exe), "process", "--help"], env=env)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
