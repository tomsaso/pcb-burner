from fbs_runtime.application_context.PyQt5 import ApplicationContext
import signal
import sys
from frmMain import init_ui

if __name__ == '__main__':
  signal.signal(signal.SIGINT, signal.SIG_DFL)
  init_ui(ApplicationContext())