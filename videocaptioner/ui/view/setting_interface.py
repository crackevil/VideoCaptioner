import webbrowser

from PyQt5.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QFileDialog, QLabel, QWidget
from qfluentwidgets import (
    ComboBoxSettingCard,
    CustomColorSettingCard,
    ExpandLayout,
    HyperlinkCard,
    InfoBar,
    OptionsSettingCard,
    PrimaryPushSettingCard,
    PushSettingCard,
    RangeSettingCard,
    ScrollArea,
    SettingCardGroup,
    SwitchSettingCard,
    setTheme,
    setThemeColor,
)
from qfluentwidgets import FluentIcon as FIF

from videocaptioner.config import AUTHOR, FEEDBACK_URL, HELP_URL, RELEASE_URL, VERSION, YEAR
from videocaptioner.core.constant import (
    INFOBAR_DURATION_ERROR,
    INFOBAR_DURATION_SUCCESS,
    INFOBAR_DURATION_WARNING,
)



from videocaptioner.ui.common.config import cfg
from videocaptioner.ui.common.signal_bus import signalBus
from videocaptioner.ui.components.EditComboBoxSettingCard import EditComboBoxSettingCard
from videocaptioner.ui.components.LineEditSettingCard import LineEditSettingCard


class SettingInterface(ScrollArea):
    """设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(self.tr("设置"))
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        self.settingLabel = QLabel(self.tr("设置"), self)

        # 初始化所有设置组
        self.__initGroups()
        # 初始化所有配置卡片
        self.__initCards()
        # 初始化界面
        self.__initWidget()
        # 初始化布局
        self.__initLayout()
        # 连接信号和槽
        self.__connectSignalToSlot()

    def __initGroups(self):
        """初始化所有设置组"""
        # 转录配置组
        self.transcribeGroup = SettingCardGroup(self.tr("转录配置"), self.scrollWidget)

        # 任务并发配置组
        self.taskGroup = SettingCardGroup(self.tr("任务配置"), self.scrollWidget)

        # 保存配置组
        self.saveGroup = SettingCardGroup(self.tr("保存配置"), self.scrollWidget)
        # 个性化组
        self.personalGroup = SettingCardGroup(self.tr("个性化"), self.scrollWidget)

    def __initCards(self):
        """初始化所有配置卡片"""

        # ASR 服务配置卡片
        self.__createASRServiceCards()

        # 任务并发配置卡片
        self.__createTaskCards()

        # 保存配置卡片
        self.savePathCard = PushSettingCard(
            self.tr("工作文件夹"),
            FIF.SAVE,
            self.tr("工作目录路径"),
            cfg.get(cfg.work_dir),
            self.saveGroup,
        )

        # 个性化配置卡片
        self.cacheEnabledCard = SwitchSettingCard(
            FIF.HISTORY,
            self.tr("启用缓存"),
            self.tr("相同配置下会复用之前的 ASR 和 LLM 结果；关闭缓存后每次重新生成"),
            cfg.cache_enabled,
            self.personalGroup,
        )
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr("应用主题"),
            self.tr("更改应用程序的外观"),
            texts=[self.tr("浅色"), self.tr("深色"), self.tr("使用系统设置")],
            parent=self.personalGroup,
        )
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr("主题颜色"),
            self.tr("更改应用程序的主题颜色"),
            self.personalGroup,
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            self.tr("界面缩放"),
            self.tr("更改小部件和字体的大小"),
            texts=["100%", "125%", "150%", "175%", "200%", self.tr("使用系统设置")],
            parent=self.personalGroup,
        )
        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr("语言"),
            self.tr("设置您偏好的界面语言"),
            texts=["简体中文", "繁體中文", "English", self.tr("使用系统设置")],
            parent=self.personalGroup,
        )

        self.saveGroup.addSettingCard(self.savePathCard)
        self.saveGroup.addSettingCard(self.cacheEnabledCard)

        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.personalGroup.addSettingCard(self.zoomCard)
        self.personalGroup.addSettingCard(self.languageCard)

    def __createASRServiceCards(self):
        """创建 ASR 配置卡片"""
        # 转录配置卡片
        self.transcribeModelCard = ComboBoxSettingCard(
            cfg.transcribe_model,
            FIF.MICROPHONE,
            self.tr("转录模型"),
            self.tr("语音转换文字要使用的语音识别服务"),
            texts=[model.value for model in cfg.transcribe_model.validator.options],  # type: ignore
            parent=self.transcribeGroup,
        )
        self.transcribeModelCard.comboBox.setMinimumWidth(150)

    def __createTaskCards(self):
        """创建任务并发相关的配置卡片"""
        # 批处理大小配置
        self.batchSizeCard = RangeSettingCard(
            cfg.batch_size,
            FIF.ALIGNMENT,
            self.tr("批处理大小"),
            self.tr("每批处理字幕的数量，建议为 10 的倍数"),
            parent=self.taskGroup,
        )

        # 线程数配置
        self.threadNumCard = RangeSettingCard(
            cfg.thread_num,
            FIF.SPEED_HIGH,
            self.tr("线程数"),
            self.tr(
                "请求并行处理的数量，模型服务商允许的情况下建议尽可能大，数值越大速度越快"
            ),
            parent=self.taskGroup,
        )

        # 添加卡片到任务配置组
        self.taskGroup.addSettingCard(self.batchSizeCard)
        self.taskGroup.addSettingCard(self.threadNumCard)

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # type: ignore
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName("settingInterface")

        # 初始化样式表
        self.scrollWidget.setObjectName("scrollWidget")
        self.settingLabel.setObjectName("settingLabel")

        # 初始化转录模型配置卡片的显示状态
        self.__onTranscribeModelChanged(self.transcribeModelCard.comboBox.currentText())

        self.setStyleSheet(
            """
            SettingInterface, #scrollWidget {
                background-color: transparent;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QLabel#settingLabel {
                font: 33px 'Microsoft YaHei';
                background-color: transparent;
                color: white;
            }
        """
        )

    def __initLayout(self):
        """初始化布局"""
        self.settingLabel.move(36, 30)

        # 添加转录配置卡片
        self.transcribeGroup.addSettingCard(self.transcribeModelCard)


        # 将所有组添加到布局
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.transcribeGroup)

        self.expandLayout.addWidget(self.taskGroup)
        self.expandLayout.addWidget(self.saveGroup)
        self.expandLayout.addWidget(self.personalGroup)

    def __connectSignalToSlot(self):
        """连接信号与槽"""
        cfg.appRestartSig.connect(self.__showRestartTooltip)

        # 转录模型切换
        self.transcribeModelCard.comboBox.currentTextChanged.connect(
            self.__onTranscribeModelChanged
        )

        # 保存路径
        self.savePathCard.clicked.connect(self.__onsavePathCardClicked)

        # 个性化
        self.themeCard.optionChanged.connect(lambda ci: setTheme(cfg.get(ci)))
        self.themeColorCard.colorChanged.connect(setThemeColor)

        # 全局 signalBus
        self.transcribeModelCard.comboBox.currentTextChanged.connect(
            signalBus.transcription_model_changed
        )

    def __showRestartTooltip(self):
        """显示重启提示"""
        InfoBar.success(
            self.tr("更新成功"),
            self.tr("配置将在重启后生效"),
            duration=INFOBAR_DURATION_SUCCESS,
            parent=self,
        )

    def __onsavePathCardClicked(self):
        """处理保存路径卡片点击事件"""
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹"), "./")
        if not folder or cfg.get(cfg.work_dir) == folder:
            return
        cfg.set(cfg.work_dir, folder)
        self.savePathCard.setContent(folder)

    def __onTranscribeModelChanged(self, model_name):
        """处理转录模型切换事件"""
        # 更新布局
        self.transcribeGroup.adjustSize()
        self.expandLayout.update()
