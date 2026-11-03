"""VideoCaptioner CLI — AI-powered video captioning from the command line.

Usage:
    videocaptioner <command> [options]

Commands:
    gui          Launch the desktop app
    transcribe   Transcribe audio/video to subtitles
    process      Full pipeline (transcribe → optimize → synthesize)
    config       Manage configuration
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from videocaptioner.cli import exit_codes as EXIT


def _configure_stdio() -> None:
    """Prefer UTF-8 CLI output, and never crash on legacy Windows encodings."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass



def _parse_output_formats_arg(value: str) -> List[str]:
    """argparse type: parse comma-separated output formats."""
    from videocaptioner.cli.validators import parse_output_formats
    try:
        return parse_output_formats(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    """Add output-related options."""
    group = parser.add_argument_group("Output options")
    group.add_argument("-o", "--output", metavar="PATH", help="Output file or directory path")
    group.add_argument(
        "--format",
        metavar="FORMATS",
        type=_parse_output_formats_arg,
        help="Comma-separated output subtitle formats: srt, ass, txt, json "
             "(default: srt). Example: --format srt,txt",
    )



def _add_common_options(parser: argparse.ArgumentParser) -> None:
    """Add options common to all commands."""
    parser.add_argument("--config", metavar="FILE", help="Path to config file")
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    verbosity.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (only output result path)")


def _build_transcribe_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "transcribe",
        help="Transcribe audio/video to subtitles",
        description="Convert audio or video files to subtitle files using ASR (Automatic Speech Recognition).",
    )
    p.add_argument("input", help="Audio or video file path")
    _add_common_options(p)
    _add_output_options(p)

    asr = p.add_argument_group("ASR options")
    asr.add_argument(
        "--asr",
        choices=["bijian", "jianying", "whisper-cpp"],
        help="ASR engine (default: bijian). "
             "bijian/jianying: free, no setup, Chinese & English only. "
             "For other languages use whisper-cpp",
    )
    asr.add_argument("--language", metavar="CODE",
                     help="Source language as ISO 639-1 code, or 'auto' (default: auto)")
    asr.add_argument("--word-timestamps", action="store_true",
                     help="Include word-level timestamps (for subtitle splitting)")

    asr.add_argument("--whisper-model", metavar="NAME",
                     help="Model name for whisper-cpp (default: large-v2)")

    # Advanced options (configurable via 'config set', hidden from --help)
    for arg in ["--fw-model", "--fw-device", "--fw-vad-method", "--fw-prompt"]:
        p.add_argument(arg, help=argparse.SUPPRESS)
    p.add_argument("--fw-vad-threshold", type=float, help=argparse.SUPPRESS)
    p.add_argument("--fw-voice-extraction", action="store_true", help=argparse.SUPPRESS)

    p.set_defaults(func=_run_transcribe)


def _build_gui_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "gui",
        help="Launch the desktop app",
        description="Launch the VideoCaptioner desktop app.",
    )
    p.set_defaults(func=_run_gui)


def _build_process_parser(subparsers) -> None:

    p = subparsers.add_parser(
        "process",
        help="Full pipeline: transcribe → optimize → synthesize",
        description="Run the complete captioning pipeline on a video or audio file: "
                    "transcribe, then optimize subtitles, then burn or embed them into video.",
    )
    p.add_argument("input", help="Video or audio file path")
    _add_common_options(p)

    _add_output_options(p)

    pipe = p.add_argument_group("Pipeline options")
    pipe.add_argument("--no-optimize", action="store_true", help="Skip AI subtitle polish")
    pipe.add_argument("--no-split", action="store_true", help="Skip subtitle re-segmentation")
    pipe.add_argument("--no-synthesize", action="store_true", help="Skip video synthesis (output subtitles only)")

    pipe.add_argument("--asr", choices=["bijian", "jianying", "whisper-cpp"],
                      help="ASR engine (default: bijian)")
    pipe.add_argument("--language", metavar="CODE",
                      help="Source language as ISO 639-1 code, or 'auto' (default: auto)")
    pipe.add_argument("--quality", choices=["ultra", "high", "medium", "low"], help="Video quality (default: medium)")
    pipe.add_argument("--subtitle-mode", choices=["soft", "hard"], help="Subtitle mode (default: soft)")
    pipe.add_argument("--layout", choices=["target-above", "source-above", "target-only", "source-only"],
                      help="Subtitle layout (default: target-above)")
    pipe.add_argument("--tts-api-key", metavar="KEY", help="Dubbing TTS API key for SiliconFlow/Gemini")
    pipe.add_argument("--voice", metavar="VOICE", help="Default dubbing voice")
    pipe.add_argument("--timing", choices=["balanced", "strict", "natural", "none"], help="Dubbing timing strategy")
    pipe.add_argument("--adapt-length", dest="rewrite_too_long", action="store_true", help="Shorten lines that are too long for their subtitle slot")
    pipe.add_argument("--audio-mode", choices=["replace", "mix", "duck"], help="How to handle original video audio")
    pipe.add_argument("--speaker-voice", action="append", default=[], metavar="NAME=VOICE",
                      help="Map subtitle speaker to a voice; repeatable")
    pipe.add_argument("--speaker-clone", action="append", default=[], metavar="NAME=AUDIO|TEXT",
                      help="Map speaker to clone reference audio and transcript; repeatable")
    pipe.add_argument("--clone-audio", metavar="FILE", help="Default speaker clone reference audio")
    pipe.add_argument("--clone-text", metavar="TEXT", help="Exact transcript for --clone-audio")
    # Hidden options
    p.add_argument("--prompt-file", metavar="FILE", help=argparse.SUPPRESS)
    p.add_argument("--prompt", metavar="TEXT", help=argparse.SUPPRESS)
    p.add_argument("--thread-num", type=int, metavar="N", help=argparse.SUPPRESS)
    p.add_argument("--batch-size", type=int, metavar="N", help=argparse.SUPPRESS)
    p.add_argument("--whisper-model", help=argparse.SUPPRESS)
    p.add_argument("--dub-provider", choices=["siliconflow", "gemini", "edge"], help=argparse.SUPPRESS)
    p.add_argument("--tts-api-base", metavar="URL", help=argparse.SUPPRESS)
    p.add_argument("--tts-model", metavar="NAME", help=argparse.SUPPRESS)
    p.add_argument("--style-prompt", metavar="TEXT", help=argparse.SUPPRESS)
    p.add_argument("--tts-workers", type=int, metavar="N", help=argparse.SUPPRESS)
    p.add_argument("--speaker-style", action="append", default=[], metavar="NAME=PROMPT", help=argparse.SUPPRESS)
    p.add_argument("--fit-mode", choices=["tempo", "none"], help=argparse.SUPPRESS)
    p.add_argument("--max-speed", type=float, metavar="N", help=argparse.SUPPRESS)
    p.add_argument("--mix-original-audio", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--rewrite-too-long", dest="rewrite_too_long", action="store_true", help=argparse.SUPPRESS)

    p.set_defaults(func=_run_process)



def _build_config_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "config",
        help="Manage configuration",
        description="View, edit, and manage VideoCaptioner configuration.",
    )
    config_sub = p.add_subparsers(dest="config_action", metavar="action")

    config_sub.add_parser("show", help="Display current configuration")
    config_sub.add_parser("path", help="Show config file path")
    init_p = config_sub.add_parser(
        "init",
        help="Create an onboarding config file",
        description=(
            "Create a VideoCaptioner config file. By default this starts an interactive setup. "
            "Use --non-interactive for Agent/CI-friendly setup."
        ),
    )
    init_p.add_argument("--non-interactive", action="store_true", help="Write config without prompts")
    init_p.add_argument("--force", action="store_true", help="Overwrite existing config file")
    init_p.add_argument("--print-template", action="store_true", help="Print a commented template instead of writing")
    init_p.add_argument("--profile", choices=["basic", "dubbing"], default="basic", help="Configuration profile")

    init_p.add_argument("--asr", choices=["bijian", "jianying", "whisper-cpp"], help="Default ASR engine")
    init_p.add_argument("--no-optimize", action="store_true", help="Disable AI subtitle polish by default")
    init_p.add_argument("--no-split", action="store_true", help="Disable subtitle re-segmentation by default")

    init_p.add_argument("--voice", metavar="VOICE", help="Default dubbing voice")
    init_p.add_argument("--timing", choices=["balanced", "strict", "natural", "none"], help="Dubbing timing strategy")
    init_p.add_argument("--audio-mode", choices=["replace", "mix", "duck"], help="Original audio handling for dubbing")
    config_sub.add_parser("edit", help="Open config file in $EDITOR")

    set_p = config_sub.add_parser("set", help="Set a configuration value")
    set_p.add_argument("key", help="Config key in dotted notation (e.g. llm.api_key)")
    set_p.add_argument("value", help="Value to set")

    get_p = config_sub.add_parser("get", help="Get a configuration value")
    get_p.add_argument("key", help="Config key in dotted notation")

    p.set_defaults(func=_run_config)


def _build_doctor_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "doctor",
        help="Diagnose dependencies and configuration",
        description="Check local tools, config, and common workflow readiness.",
    )
    _add_common_options(p)
    p.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p.add_argument("--check-api", action="store_true", help="Also perform lightweight provider API checks")
    p.set_defaults(func=_run_doctor)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="videocaptioner",
        description="AI-powered video captioning — transcribe speech, optimize subtitles, "
                    "then burn them into video with customizable styles (ASS or rounded background).",
        epilog="Run 'videocaptioner <command> --help' for details on each command.",
    )
    parser.add_argument("--version", action="version", version=_get_version())

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    _build_transcribe_parser(subparsers)
    _build_gui_parser(subparsers)
    _build_process_parser(subparsers)
    _build_config_parser(subparsers)
    _build_doctor_parser(subparsers)

    return parser


def _get_version() -> str:
    # Read version without importing config.py (avoids side effects)
    try:
        import importlib.metadata
        return f"videocaptioner {importlib.metadata.version('videocaptioner')}"
    except Exception:
        return "videocaptioner (version unknown)"


# ── Command runners ──────────────────────────────────────────────────────────


def _build_cli_overrides(args: argparse.Namespace) -> dict:
    """Extract CLI arguments into a config override dict."""
    overrides: dict = {}

    def _set(key: str, value) -> None:
        if value is not None:
            from videocaptioner.cli.config import _set_nested
            _set_nested(overrides, key, value)

    # WhisperCpp
    _set("transcribe.whisper_cpp.model", getattr(args, "whisper_model", None))

    # Transcribe
    _set("transcribe.asr", getattr(args, "asr", None))
    _set("transcribe.language", getattr(args, "language", None))

    # FasterWhisper
    _set("transcribe.faster_whisper.model", getattr(args, "fw_model", None))
    _set("transcribe.faster_whisper.device", getattr(args, "fw_device", None))
    _set("transcribe.faster_whisper.vad_method", getattr(args, "fw_vad_method", None))
    _set("transcribe.faster_whisper.vad_threshold", getattr(args, "fw_vad_threshold", None))
    if getattr(args, "fw_voice_extraction", False):
        _set("transcribe.faster_whisper.voice_extraction", True)
    _set("transcribe.faster_whisper.prompt", getattr(args, "fw_prompt", None))

    # Output
    _set("output.format", getattr(args, "format", None))

    return overrides


def _load_config(args: argparse.Namespace) -> dict:
    """Load config with all layers merged."""
    from videocaptioner.cli.config import build_config
    config_path = None
    if getattr(args, "config", None):
        config_path = Path(args.config)
        if not config_path.exists():
            from videocaptioner.cli import output
            output.warn(f"Config file not found: {config_path}, using defaults")
            config_path = None
    cli_overrides = _build_cli_overrides(args)
    return build_config(cli_overrides=cli_overrides, config_path=config_path)


def _run_transcribe(args: argparse.Namespace) -> int:
    from videocaptioner.cli.commands.transcribe import run
    config = _load_config(args)
    return run(args, config)


def _run_gui(_args: argparse.Namespace) -> int:
    try:
        from videocaptioner.ui.main import main as gui_main
    except ImportError as exc:
        print(f"GUI dependencies are not available: {exc}")
        print("Install the official package with: pip install videocaptioner")
        return EXIT.DEPENDENCY_MISSING
    gui_main()
    return EXIT.SUCCESS


def _run_process(args: argparse.Namespace) -> int:
    from videocaptioner.cli.commands.process import run
    config = _load_config(args)
    return run(args, config)


def _run_config(args: argparse.Namespace) -> int:
    from videocaptioner.cli.commands.config_cmd import run
    config = _load_config(args)
    return run(args, config)


def _run_doctor(args: argparse.Namespace) -> int:
    from videocaptioner.cli.commands.doctor import run
    config = _load_config(args)
    return run(args, config)


def _run_style(args: argparse.Namespace) -> int:
    from videocaptioner.cli.commands.style_cmd import run
    config = _load_config(args)
    return run(args, config)


def main(argv: Optional[List[str]] = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        return _run_gui(args)

    if not hasattr(args, "func"):
        parser.print_help()
        return EXIT.USAGE_ERROR

    # Control core logger output for CLI: quiet=CRITICAL, default=WARNING, verbose=DEBUG
    import logging
    quiet = getattr(args, "quiet", False)
    verbose = getattr(args, "verbose", False)
    if quiet:
        logging.getLogger().setLevel(logging.CRITICAL)
    elif verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as e:
        from videocaptioner.cli.output import error
        error(str(e))
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        return EXIT.GENERAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
