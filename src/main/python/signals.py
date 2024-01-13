from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

class Signal(QObject):
  signaled = pyqtSignal(dict)

  def __init__(self):
    QObject.__init__(self)

  def signal(self, val):
    self.signaled.emit(val)