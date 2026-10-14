from PyQt5.QtCore import QObject, QUrl, pyqtSignal


class SignalBus(QObject):

    # 转录模型
    transcription_model_changed = pyqtSignal(str)



signalBus = SignalBus()
