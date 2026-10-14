import os

from PyQt5.QtCore import Qt
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
    MessageBoxBase,
    SettingCardGroup,
    SingleDirectionScrollArea,
    SubtitleLabel,
    TableItemDelegate,
    TableWidget,
)
from qfluentwidgets import FluentIcon as FIF

from videocaptioner.config import MODEL_PATH
from videocaptioner.core.entities import (
    TranscribeLanguageEnum,
    WhisperModelEnum,
)
from videocaptioner.core.utils.platform_utils import open_folder
from videocaptioner.ui.common.config import cfg

# 使用阿里云镜像定义模型配置
# https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-tiny.bin
# "mirrorLink": "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin?download=true"

# 使用阿里云镜像定义模型配置
WHISPER_CPP_MODELS = [
    {
        "label": "Tiny",
        "value": "ggml-tiny.bin",
        "size": "77.7 MB",
        "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
        "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-tiny.bin",
        "sha": "bd577a113a864445d4c299885e0cb97d4ba92b5f",
    },
    {
        "label": "Base",
        "value": "ggml-base.bin",
        "size": "148 MB",
        "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
        "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-base.bin",
        "sha": "465707469ff3a37a2b9b8d8f89f2f99de7299dac",
    },
    {
        "label": "Small",
        "value": "ggml-small.bin",
        "size": "488 MB",
        "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
        "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-small.bin",
        "sha": "55356645c2b361a969dfd0ef2c5a50d530afd8d5",
    },
    {
        "label": "Medium",
        "value": "ggml-medium.bin",
        "size": "1.53 GB",
        "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
        "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-medium.bin",
        "sha": "fd9727b6e1217c2f614f9b698455c4ffd82463b4",
    },
    {
        "label": "large-v1",
        "value": "ggml-large-v1.bin",
        "size": "3.09 GB",
        "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v1.bin",
        "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-large-v1.bin",
        "sha": "b1caaf735c4cc1429223d5a74f0f4d0b9b59a299",
    },
    {
        "label": "large-v2",
        "value": "ggml-large-v2.bin",
        "size": "3.09 GB",
        "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v2.bin",
        "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-large-v2.bin",
        "sha": "0f4c8e34f21cf1a914c59d8b3ce882345ad349d6",
    },
    # {
    #     "label": "Large(v3)",
    #     "value": "ggml-large-v3.bin",
    #     "size": "3.09 GB",
    #     "downloadLink": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
    #     "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-large-v3.bin",
    #     "sha": "ad82bf6a9043ceed055076d0fd39f5f186ff8062"
    # },
    # {
    #     "label": "Distil Large(v3)",
    #     "value": "ggml-distil-large-v3.bin",
    #     "size": "1.52 GB",
    #     "downloadLink": "https://huggingface.co/distil-whisper/distil-large-v3-ggml/resolve/main/ggml-distil-large-v3.bin?download=true",
    #     "mirrorLink": "https://www.modelscope.cn/models/cjc1887415157/whisper.cpp/resolve/master/ggml-distil-large-v3.bin",
    #     "sha": "5e61e98bdcf3b9a78516c59bf7d1a10d64cae67a"
    # }
]


def check_whisper_cpp_exists():
    """检查WhisperCpp程序是否存在"""
    return True, []


class WhisperCppDownloadDialog(MessageBoxBase):
    """WhisperCpp 下载对话框"""

    def __init__(self, parent=None, setting_widget=None):
        super().__init__(parent)
        self.widget.setMinimumWidth(600)
        self._setup_ui()
        self.setting_widget = setting_widget

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        self._setup_program_section(layout)
        layout.addSpacing(20)
        self._setup_model_section(layout)

        self.viewLayout.addLayout(layout)
        self.cancelButton.setText(self.tr("关闭"))
        self.yesButton.hide()

    def _setup_program_section(self, layout):
        """设置程序下载部分UI"""
        # 标题
        whisper_cpp_title = SubtitleLabel(self.tr("WhisperCpp程序"), self)
        layout.addWidget(whisper_cpp_title)
        layout.addSpacing(8)

        # 检查已安装的版本
        has_program, installed_versions = check_whisper_cpp_exists()

        if has_program:
            # 显示已安装版本
            versions_text = " + ".join(installed_versions)
            program_status = BodyLabel(self.tr(f"已安装版本: {versions_text}"), self)
            program_status.setStyleSheet("color: green")
            layout.addWidget(program_status)
        else:
            desc_label = BodyLabel(self.tr("未下载 WhisperCpp 程序"), self)
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
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(
            [self.tr("模型名称"), self.tr("大小"), self.tr("状态")]
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

        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 80)

        # 设置行高
        row_height = 45
        table.verticalHeader().setDefaultSectionSize(row_height)

        # 设置表格高度
        header_height = 20
        max_visible_rows = 6
        table_height = row_height * max_visible_rows + header_height + 15
        table.setFixedHeight(table_height)

        return table

    def _populate_model_table(self):
        """填充模型表格数据"""
        self.model_table.setRowCount(len(WHISPER_CPP_MODELS))
        for i, model in enumerate(WHISPER_CPP_MODELS):
            self._add_model_row(i, model)

    def _add_model_row(self, row, model):
        """添加模型表格行"""
        # 模型名称
        name_item = QTableWidgetItem(model["label"])
        name_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        self.model_table.setItem(row, 0, name_item)

        # 大小
        size_item = QTableWidgetItem(f"{model['size']}")
        size_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        self.model_table.setItem(row, 1, size_item)

        # 状态
        model_bin_path = os.path.join(MODEL_PATH, model["value"])
        status_item = QTableWidgetItem(
            self.tr("已下载") if os.path.exists(model_bin_path) else self.tr("未下载")
        )
        if os.path.exists(model_bin_path):
            status_item.setForeground(Qt.green)  # type: ignore
        status_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
        self.model_table.setItem(row, 2, status_item)

    def _open_model_folder(self):
        """打开模型文件夹"""
        if os.path.exists(MODEL_PATH):
            # 根据操作系统打开文件夹
            open_folder(str(MODEL_PATH))


class WhisperCppSettingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_signals()

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

        self.setting_group = SettingCardGroup(self.tr("Whisper CPP 设置"), self)

        # 模型选择
        self.model_card = ComboBoxSettingCard(
            cfg.whisper_model,
            FIF.ROBOT,
            self.tr("模型"),
            self.tr("选择Whisper模型"),
            [model.value for model in WhisperModelEnum],
            self.setting_group,
        )

        # 检查未下载的模型并从下拉框中移除
        for i in range(self.model_card.comboBox.count() - 1, -1, -1):
            model_text = self.model_card.comboBox.itemText(i).lower()
            model_configs = {
                model["label"].lower(): model for model in WHISPER_CPP_MODELS
            }
            model_config = model_configs.get(model_text)
            if model_config and (MODEL_PATH / model_config["value"]).exists():
                continue
            self.model_card.comboBox.removeItem(i)

        # 语言选择
        self.language_card = ComboBoxSettingCard(
            cfg.transcribe_language,
            FIF.LANGUAGE,
            self.tr("源语言"),
            self.tr("音视频中说话的语言，默认根据前30秒自动识别"),
            [language.value for language in TranscribeLanguageEnum],
            self.setting_group,
        )

        # 添加模型管理卡片
        self.manage_model_card = HyperlinkCard(
            "",  # 无链接
            self.tr("管理模型"),
            FIF.DOWNLOAD,  # 使用下载图标
            self.tr("模型管理"),
            self.tr("下载或更新 Whisper CPP 模型"),
            self.setting_group,  # 添加到设置组
        )

        # 添加 setMaxVisibleItems
        self.language_card.comboBox.setMaxVisibleItems(6)

        # 使用 addSettingCard 添加卡片到组
        self.setting_group.addSettingCard(self.model_card)
        self.setting_group.addSettingCard(self.language_card)
        self.setting_group.addSettingCard(self.manage_model_card)

        # 将设置组添加到容器布局
        self.containerLayout.addWidget(self.setting_group)
        self.containerLayout.addStretch(1)

        # 设置组件最小宽度
        self.model_card.comboBox.setMinimumWidth(200)
        self.language_card.comboBox.setMinimumWidth(200)

        # 设置滚动区域
        self.scrollArea.setWidget(self.container)
        self.scrollArea.setWidgetResizable(True)

        # 将滚动区域添加到主布局
        self.main_layout.addWidget(self.scrollArea)

    def setup_signals(self):
        self.manage_model_card.linkButton.clicked.connect(self.show_download_dialog)

    def show_download_dialog(self):
        """显示下载对话框"""
        download_dialog = WhisperCppDownloadDialog(self.window(), self)
        download_dialog.show()
