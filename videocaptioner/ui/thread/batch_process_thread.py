import queue
import time
from functools import partial
from typing import Dict, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from videocaptioner.core.entities import (
    BatchTaskStatus,
    BatchTaskType,
)
from videocaptioner.core.utils.logger import setup_logger
from videocaptioner.ui.task_factory import TaskFactory
from videocaptioner.ui.thread.transcript_thread import TranscriptThread

logger = setup_logger("batch_process_thread")

# 当前批量处理支持的任务类型
SUPPORTED_BATCH_TASK_TYPES = (BatchTaskType.TRANSCRIBE,)


class BatchTask:
    def __init__(self, file_path: str, task_type: BatchTaskType):
        self.file_path = file_path
        self.task_type = task_type
        self.status = BatchTaskStatus.WAITING
        self.progress = 0
        self.error_message = ""
        self.current_thread: Optional[QThread] = None


class BatchProcessThread(QThread):
    # 信号定义
    task_progress = pyqtSignal(str, int, str)  # file_path, progress, status
    task_error = pyqtSignal(str, str)  # file_path, error_message
    task_completed = pyqtSignal(str)  # file_path

    def __init__(self):
        super().__init__()
        self.task_queue = queue.Queue()
        self.current_tasks: Dict[str, BatchTask] = {}
        self.max_concurrent_tasks = 1
        self.is_running = False
        self.factory = TaskFactory()
        self.threads = []  # 保存所有创建的线程

    def add_task(self, task: BatchTask):
        self.task_queue.put(task)
        self.current_tasks[task.file_path] = task
        if not self.isRunning():
            self.is_running = True
            self.start()

    def run(self):
        while self.is_running:
            # 检查是否有正在运行的任务数量是否达到上限
            running_tasks = sum(
                1
                for task in self.current_tasks.values()
                if task.status == BatchTaskStatus.RUNNING
            )

            if running_tasks < self.max_concurrent_tasks:
                try:
                    # 非阻塞方式获取任务
                    task = self.task_queue.get_nowait()
                    self._process_task(task)
                except queue.Empty:
                    time.sleep(0.1)  # 避免CPU过度使用
            else:
                time.sleep(0.1)

    def _process_task(self, batch_task: BatchTask):
        try:
            batch_task.status = BatchTaskStatus.RUNNING
            self.task_progress.emit(
                batch_task.file_path, 0, str(BatchTaskStatus.RUNNING)
            )

            if batch_task.task_type == BatchTaskType.TRANSCRIBE:
                self._handle_transcribe_task(batch_task)
            else:
                raise ValueError(f"不支持的批量任务类型: {batch_task.task_type}")

        except Exception as e:
            logger.exception(f"处理任务失败: {str(e)}")
            batch_task.status = BatchTaskStatus.FAILED
            batch_task.error_message = str(e)
            self.task_error.emit(batch_task.file_path, str(e))

    def _on_progress_wrapper(self, batch_task: BatchTask, progress: int, message: str):
        """进度信号包装器"""
        self.task_progress.emit(batch_task.file_path, progress, message)

    def _on_error_wrapper(self, batch_task: BatchTask, error: str):
        """错误信号包装器"""
        batch_task.status = BatchTaskStatus.FAILED
        batch_task.error_message = error
        self.task_error.emit(batch_task.file_path, error)

    def _on_finished_wrapper(self, batch_task: BatchTask, task=None):
        """完成信号包装器"""
        batch_task.status = BatchTaskStatus.COMPLETED
        batch_task.progress = 100
        self.task_completed.emit(batch_task.file_path)
        if batch_task.current_thread in self.threads:
            self.threads.remove(batch_task.current_thread)

    def _handle_transcribe_task(self, batch_task: BatchTask):
        # self.max_concurrent_tasks = 3
        task = self.factory.create_transcribe_task(batch_task.file_path)
        thread = TranscriptThread(task)
        batch_task.current_thread = thread

        # 保存线程引用
        self.threads.append(thread)

        thread.progress.connect(  # type: ignore
            partial(self._on_progress_wrapper, batch_task)  # type: ignore
        )
        thread.error.connect(  # type: ignore
            partial(self._on_error_wrapper, batch_task)  # type: ignore
        )
        thread.finished.connect(  # type: ignore
            partial(self._on_finished_wrapper, batch_task)  # type: ignore
        )

        thread.start()

    def stop_task(self, file_path: str):
        if file_path in self.current_tasks:
            task = self.current_tasks[file_path]
            if task.current_thread:
                if hasattr(task.current_thread, "stop"):
                    task.current_thread.stop()  # type: ignore
            del self.current_tasks[file_path]
            # 从队列中移除任务
            with self.task_queue.mutex:
                self.task_queue.queue.clear()

    def stop_all(self):
        self.is_running = False
        # 停止所有线程
        for thread in self.threads:
            if hasattr(thread, "stop"):
                thread.stop()  # type: ignore
            thread.wait()  # 等待线程结束
        self.threads.clear()
        self.current_tasks.clear()
        # 清空任务队列
        with self.task_queue.mutex:
            self.task_queue.queue.clear()
