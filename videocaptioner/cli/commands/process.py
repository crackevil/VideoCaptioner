"""process command — full pipeline: transcribe → optimize → synthesize/dub."""

import json
import os
from argparse import Namespace
from pathlib import Path

from videocaptioner.cli import exit_codes as EXIT
from videocaptioner.cli import output
from videocaptioner.cli.config import get

# Quality presets: name -> (crf, ffmpeg preset)
_QUALITY_MAP: dict[str, tuple[int, str]] = {
    "ultra": (18, "slow"),
    "high": (23, "medium"),
    "medium": (28, "medium"),
    "low": (32, "fast"),
}


def run(args: Namespace, config: dict) -> int:
    input_path = args.input
    verbose = getattr(args, "verbose", False)
    quiet = getattr(args, "quiet", False)

    no_optimize = not get(config, "subtitle.optimize", True)
    no_split = not get(config, "subtitle.split", True)
    no_synthesize = getattr(args, "no_synthesize", False)
    do_dub = getattr(args, "dub", False) or getattr(args, "dub_only", False)
    if getattr(args, "dub_only", False):
        no_synthesize = True

    # URL input not supported
    is_url = input_path.startswith("http://") or input_path.startswith("https://")
    if is_url:
        output.error("URL input is not supported in the process pipeline")
        output.hint("Provide a local media file path instead")
        return EXIT.GENERAL_ERROR

    # Validate input file first (before expensive pre-flight checks)
    path = Path(input_path)
    if not path.exists():
        output.error(f"Input file not found: {path}")
        return EXIT.FILE_NOT_FOUND

    # Auto-detect audio files and skip synthesis
    audio_extensions = {"mp3", "wav", "flac", "m4a", "ogg", "opus", "aac", "wma"}
    is_audio_input = path.suffix.lstrip(".").lower() in audio_extensions
    if is_audio_input and not no_synthesize:
        no_synthesize = True
        if not quiet:
            output.info("Audio file detected, skipping video synthesis")

    # Pre-flight validation
    from videocaptioner.cli.validators import validate_dubbing, validate_process
    if not validate_process(config, no_synthesize=no_synthesize):
        return EXIT.USAGE_ERROR
    if do_dub and not validate_dubbing(
        config,
        needs_video=path.suffix.lstrip(".").lower() not in audio_extensions,
        rewrite=bool(get(config, "dubbing.rewrite_too_long", False)),
    ):
        return EXIT.USAGE_ERROR

    out_arg = getattr(args, "output", None)
    if out_arg:
        out_path = Path(out_arg)
        # If it looks like a file path (has extension), use its parent as dir
        out_dir = out_path.parent if out_path.suffix else out_path
    else:
        out_dir = path.parent

    total_steps = 2 + (0 if no_synthesize else 1) + (1 if do_dub else 0)
    current_step = 1
    final_output_path = _resolve_final_output_path(out_arg, out_dir, path, do_dub, no_synthesize, is_audio_input)
    dubbed_video_path: str | None = None

    # Step 1: Transcribe
    if not quiet:
        output.info(f"Step {current_step}/{total_steps}: Transcribing...")
    subtitle_path = str(out_dir / f"{path.stem}.srt")

    # Word timestamps are useful for semantic splitting/optimization, but bad for
    # direct dubbing because they create word-level TTS fragments.
    need_word_ts = not (no_optimize and no_split)
    tr_args = Namespace(
        input=str(path), output=subtitle_path, format="srt", word_timestamps=need_word_ts,
        verbose=verbose, quiet=quiet, config=getattr(args, "config", None),
        asr=getattr(args, "asr", None), language=getattr(args, "language", None),
        fw_model=None, fw_device=None, fw_vad_method=None, fw_vad_threshold=None,
        fw_voice_extraction=False, fw_prompt=None,
        whisper_model=None,
    )
    from videocaptioner.cli.commands.transcribe import run as transcribe_run
    ret = transcribe_run(tr_args, config)
    if ret != 0:
        return ret
    current_step += 1

    if not quiet:
        output.success("Pipeline complete!")
    return EXIT.SUCCESS







def _resolve_final_output_path(
    output_arg: str | None,
    out_dir: Path,
    input_path: Path,
    do_dub: bool,
    no_synthesize: bool,
    is_audio: bool,
) -> str:
    if output_arg:
        out_path = Path(output_arg)
        if out_path.suffix:
            return str(out_path)
    suffix = ".wav" if is_audio and do_dub else input_path.suffix
    if do_dub and no_synthesize:
        return str(out_dir / f"{input_path.stem}_dubbed{suffix}")
    if do_dub:
        return str(out_dir / f"{input_path.stem}_dubbed_captioned{suffix}")
    return str(out_dir / f"{input_path.stem}_captioned{suffix}")
