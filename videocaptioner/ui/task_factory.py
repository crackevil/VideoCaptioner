import datetime
from pathlib import Path
from typing import Optional

from videocaptioner.config import MODEL_PATH
from videocaptioner.core.entities import (
    LANGUAGES,
    TranscribeConfig,
    TranscribeTask,
)
from videocaptioner.ui.common.config import cfg


class TaskFactory:
    """任务工厂类，用于创建各种类型的任务"""

    @staticmethod
    def create_transcribe_task(
        file_path: str,
        need_next_task: bool = False,
        task_id: Optional[str] = None,
    ) -> TranscribeTask:
        """创建转录任务"""
        # 获取文件名
        file_name = Path(file_path).stem

        # 构建输出路径
        if need_next_task:
            need_word_time_stamp = cfg.need_split.value
            output_path = str(
                Path(cfg.work_dir.value)
                / file_name
                / "subtitle"
                / f"【原始字幕】{file_name}-{cfg.transcribe_model.value.value}-{cfg.transcribe_language.value.value}.srt"
            )
        else:
            need_word_time_stamp = False
            output_path = str(Path(file_path).parent / f"{file_name}.srt")

        config = TranscribeConfig(
            transcribe_model=cfg.transcribe_model.value,
            transcribe_language=LANGUAGES[cfg.transcribe_language.value.value],
            need_word_time_stamp=need_word_time_stamp,
            output_format=cfg.transcribe_output_format.value,
            # Whisper Cpp 配置
            whisper_model=cfg.whisper_model.value,
            # Faster Whisper 配置
            faster_whisper_program=cfg.faster_whisper_program.value,
            faster_whisper_model=cfg.faster_whisper_model.value,
            faster_whisper_model_dir=str(MODEL_PATH),
            faster_whisper_device=cfg.faster_whisper_device.value,
            faster_whisper_vad_filter=cfg.faster_whisper_vad_filter.value,
            faster_whisper_vad_threshold=cfg.faster_whisper_vad_threshold.value,
            faster_whisper_vad_method=cfg.faster_whisper_vad_method.value,
            faster_whisper_ff_mdx_kim2=cfg.faster_whisper_ff_mdx_kim2.value,
            faster_whisper_one_word=cfg.faster_whisper_one_word.value,
            faster_whisper_prompt=cfg.faster_whisper_prompt.value,
        )

        task = TranscribeTask(
            queued_at=datetime.datetime.now(),
            file_path=file_path,
            output_path=output_path,
            transcribe_config=config,
            need_next_task=need_next_task,
        )
        if task_id:
            task.task_id = task_id
        return task
