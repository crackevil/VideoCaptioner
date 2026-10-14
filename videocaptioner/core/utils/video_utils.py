import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Literal, Optional

from ..entities import (
    AudioStreamInfo,
    SubtitleLayoutEnum,
    VideoInfo,
)


from ..utils.logger import setup_logger

if TYPE_CHECKING:
    from videocaptioner.core.asr.asr_data import ASRData

# FFmpeg preset 类型
PresetType = Literal[
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
]

logger = setup_logger("video_utils")


@contextmanager
def temporary_subtitle_file(subtitle_path: str):
    """临时字幕文件上下文管理器

    自动复制字幕文件到临时位置，使用后自动清理

    Args:
        subtitle_path: 原始字幕文件路径

    Yields:
        临时字幕文件路径
    """
    suffix = Path(subtitle_path).suffix.lower()
    temp_fd, temp_path = tempfile.mkstemp(
        suffix=suffix, prefix="VideoCaptioner_subtitle_"
    )
    os.close(temp_fd)

    try:
        # 复制字幕到临时位置
        shutil.copy2(subtitle_path, temp_path)
        yield temp_path
    finally:
        # 自动清理临时文件
        Path(temp_path).unlink(missing_ok=True)


def video2audio(input_file: str, output: str = "", audio_track_index: int = 0) -> bool:
    """使用 ffmpeg 将视频转换为音频

    Args:
        input_file: 输入视频文件路径
        output: 输出音频文件路径
        audio_track_index: 要提取的音轨索引，默认为 0（第一 audio tracks）

    Returns:
        转换是否成功
    """
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = str(output_path)

    logger.debug(f"Extracting audio track {audio_track_index}")
    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-map",
        f"0:a:{audio_track_index}",
        "-vn",
        "-ac",
        "1",  # 单声道
        "-ar",
        "16000",  # 采样率16kHz
        "-y",
        output,
    ]

    logger.debug(f"Audio conversion cmd: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            ),
        )
        if result.returncode == 0 and Path(output).is_file():
            logger.debug("Audio conversion complete")
            return True
        else:
            logger.error("Audio conversion failed")
            return False
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg execution failed")
        logger.error(f"Return code: {e.returncode}")
        logger.error(f"Command: {' '.join(e.cmd)}")
        if e.stdout:
            logger.error(f"stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.exception(f"音频转换出错: {str(e)}")
        return False


def check_cuda_available() -> bool:
    """Check if CUDA hardware acceleration is available via FFmpeg."""
    try:
        # 首先检查ffmpeg是否支持cuda
        result = subprocess.run(
            ["ffmpeg", "-hwaccels"],
            capture_output=True,
            text=True,
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            ),
        )
        if "cuda" not in result.stdout.lower():
            logger.debug("CUDA not in FFmpeg hwaccels list")
            return False

        # 进一步检查CUDA设备信息
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-init_hw_device", "cuda"],
            capture_output=True,
            text=True,
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            ),
        )

        # 如果stderr中包含"Cannot load cuda" 或 "Failed to load"等Error output，说明CUDA不可用
        if any(
            error in result.stderr.lower()
            for error in ["cannot load cuda", "failed to load", "error"]
        ):
            logger.debug("CUDA device init failed")
            return False

        logger.debug("CUDA available")
        return True

    except Exception as e:
        logger.exception(f"CUDA check error: {str(e)}")
        return False



def get_video_info(
    file_path: str, thumbnail_path: Optional[str] = None
) -> Optional["VideoInfo"]:
    """获取媒体文件信息（支持视频和音频文件）

    Args:
        file_path: 媒体文件路径（视频或音频）
        thumbnail_path: 缩略图保存路径（可选，仅对视频文件有效）

    Returns:
        VideoInfo 对象，失败返回 None
        对于纯音频文件，视频相关字段（width/height/fps）将为 0
    """
    try:
        # 执行 ffmpeg 获取视频信息
        result = subprocess.run(
            ["ffmpeg", "-i", file_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            ),
        )
        info = result.stderr

        # 提取时长
        duration_seconds = 0.0
        if duration_match := re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", info):
            hours, minutes, seconds = map(float, duration_match.groups())
            duration_seconds = hours * 3600 + minutes * 60 + seconds

        # 提取比特率
        bitrate_kbps = 0
        if bitrate_match := re.search(r"bitrate: (\d+) kb/s", info):
            bitrate_kbps = int(bitrate_match.group(1))

        # 提取视频流信息
        width, height, fps, video_codec = 0, 0, 0.0, ""
        has_video_stream = False
        if video_stream_match := re.search(
            r"Stream #.*?Video: (\w+)(?:\s*\([^)]*\))?.* (\d+)x(\d+).*?(?:(\d+(?:\.\d+)?)\s*(?:fps|tb[rn]))",
            info,
            re.DOTALL,
        ):
            video_codec = video_stream_match.group(1)
            width = int(video_stream_match.group(2))
            height = int(video_stream_match.group(3))
            fps = float(video_stream_match.group(4))
            has_video_stream = True

        # 提取第一条音频流信息（用于兼容性）
        audio_codec, audio_sampling_rate = "", 0
        if audio_stream_match := re.search(
            r"Stream #\d+:\d+.*Audio: (\w+).* (\d+) Hz", info
        ):
            audio_codec = audio_stream_match.group(1)
            audio_sampling_rate = int(audio_stream_match.group(2))

        # 提取All音频流信息（用于多音轨选择）
        audio_streams: list[AudioStreamInfo] = []
        for match in re.finditer(
            r"Stream #\d+:(\d+)(?:\[0x[0-9a-fA-F]+\])?(?:\(([a-z]{3})\))?: Audio: (\w+)",
            info,
        ):
            audio_streams.append(
                AudioStreamInfo(
                    index=int(match.group(1)),
                    codec=match.group(3),
                    language=match.group(2) or "",
                )
            )

        if audio_streams:
            logger.debug(f"Detected {len(audio_streams)}  audio tracks")

        # 验证文件是否包含有效的媒体流
        if not has_video_stream and not audio_streams:
            logger.error("File has no video or audio streams")
            return None

        # 提取缩略图（如果指定了路径且有视频流）
        final_thumbnail_path = ""
        if thumbnail_path and duration_seconds > 0 and has_video_stream:
            if _extract_thumbnail(file_path, duration_seconds * 0.3, thumbnail_path):
                final_thumbnail_path = thumbnail_path

        # 构造并返回 VideoInfo 对象
        return VideoInfo(
            file_name=Path(file_path).stem,
            file_path=file_path,
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration_seconds,
            bitrate_kbps=bitrate_kbps,
            video_codec=video_codec,
            audio_codec=audio_codec,
            audio_sampling_rate=audio_sampling_rate,
            thumbnail_path=final_thumbnail_path,
            audio_streams=audio_streams,
        )
    except Exception as e:
        logger.exception(f"获取视频信息时出错: {str(e)}")
        return None


def _extract_thumbnail(video_path: str, seek_time: float, thumbnail_path: str) -> bool:
    """提取视频缩略图

    Args:
        video_path: 视频文件路径
        seek_time: 截取时间点（秒）
        thumbnail_path: 缩略图保存路径

    Returns:
        是否成功
    """
    if not Path(video_path).is_file():
        logger.error(f"视频文件不存在: {video_path}")
        return False

    try:
        timestamp = f"{int(seek_time // 3600):02}:{int((seek_time % 3600) // 60):02}:{seek_time % 60:06.3f}"
        Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                "ffmpeg",
                "-ss",
                timestamp,
                "-i",
                Path(video_path).as_posix(),
                "-vframes",
                "1",
                "-q:v",
                "2",
                "-y",
                Path(thumbnail_path).as_posix(),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=(
                getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            ),
        )
        return result.returncode == 0

    except Exception as e:
        logger.exception(f"提取缩略图时出错: {str(e)}")
        return False

