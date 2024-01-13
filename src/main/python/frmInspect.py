from PyQt5 import QtCore, QtWidgets, uic
from functools import partial
from threading import Timer

class InspectUI(QtWidgets.QDialog):
  def __init__(self, parent):
    QtWidgets.QDialog.__init__(self, parent)

    self.timeout = int(parent.ctx.config.get('reboot_timeout', 15))
    self.result = False

    ui = parent.ctx.get_resource('inspect-dialog.ui')
    uic.loadUi(ui, self)

    self.btnGood.setEnabled(False)
    self.btnBad.setEnabled(False)
    self.btnGood.clicked.connect(partial(self.reportResult, True))
    self.btnBad.clicked.connect(partial(self.reportResult, False))

    self.setStyleSheet('QWidget {font-family: "Trebuchet MS"; font-size: 13pt;}')
    self.setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)
    self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)

    self.show()
    self.countdown()

  def countdown(self):
    self.lblCountdown.setText('REBOOTING.. WAIT {0} SECONDS...'.format(self.timeout))

    if (self.timeout == 0):
      self.btnGood.setEnabled(True)
      self.btnBad.setEnabled(True)
    else:
      t = Timer(1, self.countdown)
      t.start()

    self.timeout -= 1

  def reportResult(self, result):
    self.result = result
    self.close()