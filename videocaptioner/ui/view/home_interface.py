from typing import Optional

from PyQt5.QtWidgets import QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import SegmentedWidget


from videocaptioner.ui.task_factory import TaskFactory

from videocaptioner.ui.view.transcription_interface import TranscriptionInterface


class HomeInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_task_id: Optional[str] = None  # 当前流程的任务 ID

        # 设置对象名称和样式
        self.setObjectName("HomeInterface")
        self.setStyleSheet(
            """
            HomeInterface{background: white}
        """
        )

        # 创建分段控件和堆叠控件
        self.pivot = SegmentedWidget(self)
        self.pivot.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        # 添加子界面

        self.transcription_interface = TranscriptionInterface(self)

        self.addSubInterface(
            self.transcription_interface, "TranscriptionInterface", self.tr("语音转录")
        )

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 10, 30, 30)


        self.pivot.setCurrentItem("TranscriptionInterface")

    def addSubInterface(self, widget, objectName, text):
        # 添加子界面到堆叠控件和分段控件
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def onCurrentIndexChanged(self, index):
        # 当堆叠控件的当前索引改变时，更新分段控件的当前项
        widget = self.stackedWidget.widget(index)
        if widget:
            self.pivot.setCurrentItem(widget.objectName())

    def closeEvent(self, event):
        # 关闭事件，关闭所有子界面
        self.transcription_interface.close()
        super().closeEvent(event)
