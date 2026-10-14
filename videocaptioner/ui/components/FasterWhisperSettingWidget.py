import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    ComboBoxSettingCard,
    HyperlinkButton,
    HyperlinkCard,
    InfoBar,
    InfoBarPosition,
    MessageBoxBase,
    ProgressBar,
    SettingCardGroup,
    SingleDirectionScrollArea,
    SubtitleLabel,
    SwitchSettingCard,
    TableItemDelegate,
    TableWidget,
)
from qfluentwidgets import FluentIcon as FIF

from videocaptioner.config import BIN_PATH, MODEL_PATH
from videocaptioner.core.entities import (
    FasterWhisperModelEnum,
    TranscribeLanguageEnum,
    VadMethodEnum,
)
from videocaptioner.core.utils.platform_utils import open_folder
from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.components.LineEditSettingCard import LineEditSettingCard
from videocaptioner.ui.components.SpinBoxSettingCard import DoubleSpinBoxSettingCard


FASTER_WHISPER_MODELS = [
    {
        "label": "Tiny",
        "value": "faster-whisper-tiny",
        "size": "77824",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-tiny",
        "modelScopeLink": "pengzhendong/faster-whisper-tiny",
    },
    {
        "label": "Base",
        "value": "faster-whisper-base",
        "size": "148480",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-base",
        "modelScopeLink": "pengzhendong/faster-whisper-base",
    },
    {
        "label": "Small",
        "value": "faster-whisper-small",
        "size": "495616",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-small",
        "modelScopeLink": "pengzhendong/faster-whisper-small",
    },
    {
        "label": "Medium",
        "value": "faster-whisper-medium",
        "size": "1572864",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-medium",
        "modelScopeLink": "pengzhendong/faster-whisper-medium",
    },
    {
        "label": "Large-v1",
        "value": "faster-whisper-large-v1",
        "size": "3145728",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-large-v1",
        "modelScopeLink": "pengzhendong/faster-whisper-large-v1",
    },
    {
        "label": "Large-v2",
        "value": "faster-whisper-large-v2",
        "size": "3145728",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-large-v2",
        "modelScopeLink": "pengzhendong/faster-whisper-large-v2",
    },
    {
        "label": "Large-v3",
        "value": "faster-whisper-large-v3",
        "size": "3145728",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-large-v3",
        "modelScopeLink": "pengzhendong/faster-whisper-large-v3",
    },
    {
        "label": "Large-v3-turbo",
        "value": "faster-whisper-large-v3-turbo",
        "size": "1720320",
        "downloadLink": "https://huggingface.co/Systran/faster-whisper-large-v3-turbo",
        "modelScopeLink": "pengzhendong/faster-whisper-large-v3-turbo",
    },
]


# 在类外添加这个工具函数
def check_faster_whisper_exists() -> tuple[bool, list[str]]:
    """检查 faster-whisper 程序是否存在

    检查以下两种情况:
    1. bin目录下是否有 faster-whisper.exe
    2. bin目录下是否有 Faster-Whisper-XXL/faster-whisper-xxl.exe

    Returns:
        tuple[bool, list[str]]: (是否存在程序, 已安装的版本列表)
    """
    bin_path = Path(BIN_PATH)
    installed_versions = []

    # 检查 faster-whisper.exe(CPU版本)
    if (bin_path / "faster-whisper.exe").exists():
        installed_versions.append("CPU")

    # 检查 Faster-Whisper-XXL/faster-whisper-xxl.exe(GPU版本)
    xxl_path = bin_path / "Faster-Whisper-XXL" / "faster-whisper-xxl.exe"
    if xxl_path.exists():
        installed_versions.extend(["GPU", "CPU"])
    installed_versions = list(set(installed_versions))

    return bool(installed_versions), installed_versions


class FasterWhisperDownloadDialog(MessageBoxBase):
    """Faster Whisper 下载对话框"""

    # 添加类变量跟踪下载状态
    is_downloading = False

    def __init__(self, parent=None, setting_widget=None):
        super().__init__(parent)
        self.widget.setMinimumWidth(600)
        self.model_download_thread = None
        self._setup_ui()
        self._connect_signals()
        self.setting_widget = setting_widget

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        self._setup_program_section(layout)
        layout.addSpacing(20)
        self._setup_model_section(layout)
        self._setup_progress_section(layout)

        self.viewLayout.addLayout(layout)
        self.cancelButton.setText(self.tr("关闭"))
        self.yesButton.hide()

    def _setup_program_section(self, layout):
        """设置程序下载部分UI"""
        # 标题和按钮的水平布局
        title_layout = QHBoxLayout()

        # 标题
        faster_whisper_title = SubtitleLabel(self.tr("Faster Whisper 下载"), self)
        title_layout.addWidget(faster_whisper_title)

        # 添加打开文件夹按钮
        open_folder_btn = HyperlinkButton("", self.tr("打开程序文件夹"), parent=self)
        open_folder_btn.setIcon(FIF.FOLDER)
        open_folder_btn.clicked.connect(self._open_program_folder)
        title_layout.addStretch()
        title_layout.addWidget(open_folder_btn)

        layout.addLayout(title_layout)
        layout.addSpacing(8)

        # 检查已安装的版本
        has_program, installed_versions = check_faster_whisper_exists()

        if has_program:
            # 显示已安装版本
            versions_text = " + ".join(installed_versions)
            program_status = BodyLabel(self.tr(f"已安装版本: {versions_text}"), self)
            program_status.setStyleSheet("color: green")
            layout.addWidget(program_status)

            # 添加说明标签
            if len(installed_versions) == 1:
                desc_label = BodyLabel(self.tr("您可以继续下载其他版本:"), self)
                layout.addWidget(desc_label)
        else:
            desc_label = BodyLabel(self.tr("未下载Faster Whisper 程序"), self)
            layout.addWidget(desc_label)

    def _setup_model_section(self, layout):
        """设置模型下载部分UI"""
        # 标题和按钮的水平布局
        title_layout = QHBoxLayout()

        # 标题
        model_title = SubtitleLabel(self.tr("模型下载"), self)
        title_layout.addWidget(model_title)

        # 添加打开文件夹按钮
        open_folder_btn = HyperlinkButton("", self.tr("打开模型文件夹"), parent=self)
        open_folder_btn.setIcon(FIF.FOLDER)
        open_folder_btn.clicked.connect(self._open_model_folder)
        title_layout.addStretch()
        title_layout.addWidget(open_folder_btn)

        layout.addLayout(title_layout)
        layout.addSpacing(8)

        # 模型表格
        self.model_table = self._create_model_table()
        self._populate_model_table()
        layout.addWidget(self.model_table)

    def _create_model_table(self):
        """创建模型表格"""
        table = TableWidget(self)
        table.setEditTriggers(TableWidget.NoEditTriggers)
        table.setSelectionMode(TableWidget.NoSelection)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(
            [self.tr("模型名称"), self.tr("大小"), self.tr("状态"), self.tr("操作")]
        )

        # 设置表格样式
        table.setBorderVisible(True)
        table.setBorderRadius(8)
        table.setItemDelegate(TableItemDelegate(table))

        # 设置列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)

        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 80)
        table.setColumnWidth(3, 150)

        # 设置行高
        row_height = 45
        table.verticalHeader().setDefaultSectionSize(row_height)

        # 设置表格高度
        header_height = 20
        max_visible_rows = 6
        table_height = row_height * max_visible_rows + header_height + 15
        table.setFixedHeight(table_height)

        return table

    def _setup_progress_section(self, layout):
        """设置进度显示部分UI"""
        self.progress_bar = ProgressBar(self)
        self.progress_label = BodyLabel("", self)
        self.progress_bar.hide()
        self.progress_label.hide()

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)

    def _populate_model_table(self):
        """填充模型表格数据"""
        self.model_table.setRowCount(len(FASTER_WHISPER_MODELS))
        for i, model in enumerate(FASTER_WHISPER_MODELS):
            self._add_model_row(i, model)

    def _add_model_row(self, row, model):
        """添加模型表格行"""
        # 模型名称
        name_item = QTableWidgetItem(model["label"])
        name_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        self.model_table.setItem(row, 0, name_item)

        # 大小
        size_item = QTableWidgetItem(f"{int(model['size']) / 1024:.1f} MB")
        size_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        self.model_table.setItem(row, 1, size_item)

        # 状态 - 检查model.bin文件是否存在
        model_path = os.path.join(MODEL_PATH, model["value"])
        model_bin_path = os.path.join(model_path, "model.bin")
        is_downloaded = os.path.exists(model_bin_path)

        status_item = QTableWidgetItem(
            self.tr("已下载") if is_downloaded else self.tr("未下载")
        )
        if is_downloaded:
            status_item.setForeground(Qt.green)  # type: ignore
        status_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        self.model_table.setItem(row, 2, status_item)

        # 下载按钮
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(4, 4, 4, 4)

        download_btn = HyperlinkButton(
            "",
            self.tr("重新下载") if is_downloaded else self.tr("下载"),
            parent=self,
        )
        download_btn.setIcon(FIF.DOWNLOAD)

        button_layout.addStretch()
        button_layout.addWidget(download_btn)
        button_layout.addStretch()
        self.model_table.setCellWidget(row, 3, button_container)

    def _connect_signals(self):
        """连接信号"""
        self.rejected.connect(self._on_dialog_reject)

    def _on_dialog_reject(self):
        """对话框关闭处理"""
        if self.model_download_thread and self.model_download_thread.isRunning():
            self.model_download_thread.terminate()
        FasterWhisperDownloadDialog.is_downloading = False
        self.reject()

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        self._on_dialog_reject()
        super().closeEvent(event)

    def _set_all_download_buttons_enabled(self, enabled: bool):
        """设置所有下载按钮的启用状态"""
        # 设置所有模型下载按钮
        for row in range(self.model_table.rowCount()):
            button_container = self.model_table.cellWidget(row, 3)
            if button_container:
                download_btn = button_container.findChild(HyperlinkButton)
                if download_btn:
                    download_btn.setEnabled(enabled)

    def _open_model_folder(self):
        """打开模型文件夹"""
        if os.path.exists(MODEL_PATH):
            # 根据操作系统打开文件夹
            open_folder(str(MODEL_PATH))

    def _open_program_folder(self):
        """打开程序文件夹"""
        if os.path.exists(BIN_PATH):
            # 根据操作系统打开文件夹
            open_folder(str(BIN_PATH))


class FasterWhisperSettingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._connect_signals()

    def showEvent(self, a0: QShowEvent) -> None:
        super().showEvent(a0)
        # 检查Faster Whisper模型是否存在
        is_faster_whisper_exists, _ = check_faster_whisper_exists()
        if not is_faster_whisper_exists:
            self.show_error_info(self.tr("Faster Whisper程序不存在，请先下载程序"))
            self._show_model_manager()
        return

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)

        # 创建单向滚动区域和容器
        self.scrollArea = SingleDirectionScrollArea(orient=Qt.Vertical, parent=self)  # type: ignore
        self.scrollArea.setStyleSheet(
            "QScrollArea{background: transparent; border: none}"
        )

        self.container = QWidget(self)
        self.container.setStyleSheet("QWidget{background: transparent}")
        self.containerLayout = QVBoxLayout(self.container)

        self.setting_group = SettingCardGroup(
            self.tr("Faster Whisper 设置"), self
        )

        # 模型选择
        self.model_card = ComboBoxSettingCard(
            cfg.faster_whisper_model,
            FIF.ROBOT,
            self.tr("模型"),
            self.tr("选择 Faster Whisper 模型"),
            [model.value for model in FasterWhisperModelEnum],
            self.setting_group,
        )

        # 检查未下载的模型并从下拉框中移除
        for i in range(self.model_card.comboBox.count() - 1, -1, -1):
            model_text = self.model_card.comboBox.itemText(i).lower()
            model_config = next(
                (
                    model
                    for model in FASTER_WHISPER_MODELS
                    if model["label"].lower() == model_text
                ),
                None,
            )
            if model_config:
                model_path = Path(MODEL_PATH) / model_config["value"]
                model_bin_path = model_path / "model.bin"
                if model_bin_path.exists():
                    continue
            self.model_card.comboBox.removeItem(i)

        # 创建管理模型卡片
        self.manage_model_card = HyperlinkCard(
            "",  # 无链接
            self.tr("管理模型"),
            FIF.DOWNLOAD,  # 使用下载图标
            self.tr("模型管理"),
            self.tr("下载或更新 Faster Whisper 模型"),
            self.setting_group,  # 添加到设置组
        )

        # 语言选择
        self.language_card = ComboBoxSettingCard(
            cfg.transcribe_language,
            FIF.LANGUAGE,
            self.tr("源语言"),
            self.tr("音视频中说话的语言，默认根据前30秒自动识别"),
            [lang.value for lang in TranscribeLanguageEnum],
            self.setting_group,
        )
        self.language_card.comboBox.setMaxVisibleItems(6)

        # 设备选择
        self.device_card = ComboBoxSettingCard(
            cfg.faster_whisper_device,
            FIF.IOT,
            self.tr("运行设备"),
            self.tr("模型运行设备"),
            ["cuda", "cpu"],
            self.setting_group,
        )
        # _, available_devices = check_faster_whisper_exists()
        # if "GPU" not in available_devices:
        #     self.device_card.comboBox.removeItem(0)

        # VAD设置组
        self.vad_group = SettingCardGroup(self.tr("VAD设置"), self)

        # VAD过滤开关
        self.vad_filter_card = SwitchSettingCard(
            FIF.CHECKBOX,
            self.tr("VAD过滤"),
            self.tr("过滤无人声语音片断，减少幻觉"),
            cfg.faster_whisper_vad_filter,
            self.vad_group,
        )

        # VAD阈值
        self.vad_threshold_card = DoubleSpinBoxSettingCard(
            cfg.faster_whisper_vad_threshold,
            FIF.VOLUME,  # type: ignore
            self.tr("VAD阈值"),
            self.tr("语音概率阈值，高于此值视为语音"),
            minimum=0.00,
            maximum=1.00,
            decimals=2,
            step=0.05,
        )

        # VAD方法
        self.vad_method_card = ComboBoxSettingCard(
            cfg.faster_whisper_vad_method,
            FIF.MUSIC,
            self.tr("VAD方法"),
            self.tr("选择VAD检测方法"),
            [method.value for method in VadMethodEnum],
            self.vad_group,
        )

        # 其他设置组
        self.other_group = SettingCardGroup(self.tr("其他设置"), self)

        # 音频降噪
        self.ff_mdx_kim2_card = SwitchSettingCard(
            FIF.MUSIC,
            self.tr("人声分离"),
            self.tr("处理前使用MDX-Net降噪，分离人声和背景音乐"),
            cfg.faster_whisper_ff_mdx_kim2,
            self.other_group,
        )

        # 单词时间戳
        self.one_word_card = SwitchSettingCard(
            FIF.UNIT,
            self.tr("单字时间戳"),
            self.tr("开启生成单字级时间戳；关闭后使用原始分段断句"),
            cfg.faster_whisper_one_word,
            self.other_group,
        )

        # 提示词
        self.prompt_card = LineEditSettingCard(
            cfg.faster_whisper_prompt,
            FIF.CHAT,
            self.tr("提示词"),
            self.tr("可选的提示词,默认空"),
            "",
            self.other_group,
        )

        # 添加模型设置组的卡片
        self.setting_group.addSettingCard(self.model_card)
        self.setting_group.addSettingCard(self.manage_model_card)
        self.setting_group.addSettingCard(self.device_card)
        self.setting_group.addSettingCard(self.language_card)

        # 添加VAD设置组的卡片
        self.vad_group.addSettingCard(self.vad_filter_card)
        self.vad_group.addSettingCard(self.vad_threshold_card)
        self.vad_group.addSettingCard(self.vad_method_card)

        # 添加其他设置的卡片
        self.other_group.addSettingCard(self.ff_mdx_kim2_card)
        self.other_group.addSettingCard(self.one_word_card)
        self.other_group.addSettingCard(self.prompt_card)

        # 将所有设置组添加到容器布局
        self.containerLayout.addWidget(self.setting_group)
        self.containerLayout.addWidget(self.vad_group)
        self.containerLayout.addWidget(self.other_group)
        self.containerLayout.addStretch(1)

        # 设置组件最小宽度
        self.model_card.comboBox.setMinimumWidth(200)
        self.device_card.comboBox.setMinimumWidth(200)
        self.language_card.comboBox.setMinimumWidth(200)
        self.vad_method_card.comboBox.setMinimumWidth(200)
        self.prompt_card.lineEdit.setMinimumWidth(200)

        # 设置滚动区域
        self.scrollArea.setWidget(self.container)
        self.scrollArea.setWidgetResizable(True)

        # 将滚动区域添加到主布局
        self.main_layout.addWidget(self.scrollArea)

    def _connect_signals(self):
        """连接信号"""
        self.manage_model_card.linkButton.clicked.connect(self._show_model_manager)
        self.vad_filter_card.checkedChanged.connect(self._on_vad_filter_changed)

    def _on_vad_filter_changed(self, checked: bool):
        """VAD过滤开关状态改变时的处理"""
        self.vad_threshold_card.setEnabled(checked)
        self.vad_method_card.setEnabled(checked)

    def _show_model_manager(self):
        """显示模型管理对话框"""
        dialog = FasterWhisperDownloadDialog(self.window(), self)
        dialog.exec_()

    def show_error_info(self, error_msg):
        """显示错误信息"""
        InfoBar.error(
            title=self.tr("错误"),
            content=error_msg,
            parent=self.window(),
            duration=5000,
            position=InfoBarPosition.BOTTOM,
        )

    def check_faster_whisper_model(self):
        """检查选定的Faster Whisper模型是否存在

        Returns:
            bool: 如果模型存在且配置正确返回True，否则返回False
        """
        # 检查程序是否存在
        has_program, _ = check_faster_whisper_exists()
        if not has_program:
            self.show_error_info(self.tr("Faster Whisper程序不存在，请先下载程序"))
            return False

        model_value = cfg.faster_whisper_model.value.value
        # 检查模型配置是否存在
        model_config = next(
            (
                m
                for m in FASTER_WHISPER_MODELS
                if m["label"].lower() == model_value.lower()
            ),
            None,
        )
        if not model_config:
            self.show_error_info(self.tr("模型配置不存在"))
            return False

        model_path = MODEL_PATH / model_config["value"]
        model_files = model_path / "model.bin"
        # 检查模型文件是否存在
        if not model_path.exists() and not model_files.exists():
            self.show_error_info(self.tr("模型文件不存在: ") + model_value)
            return False
        return True
