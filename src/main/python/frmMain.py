import sys, os, time, threading
import pandas as pd
import numpy as np
import espwrapper
import signals
from frmInspect import InspectUI
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from functools import partial
from datetime import datetime
from serialport import SerialPort, get_com_ports

green = QtGui.QBrush(QtGui.QColor.fromRgb(62, 222, 102))
red = QtGui.QBrush(QtGui.QColor.fromRgb(245, 66, 69))
lightgray = QtGui.QBrush(QtGui.QColor.fromRgb(207, 207, 207))

bool_cols = ['passed_test', 'printed']
common_bins = ['a.bin', 'b.bin', 'c.bin', 'd.bin']

class Ui(QtWidgets.QMainWindow):
  def __init__(self, ctx):
    super(Ui, self).__init__()

    self.ctx = ctx
    ui = ctx.get_resource('main-window.ui')
    uic.loadUi(ui, self)

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    self.base_path = ui.replace('main-window.ui', '')
    self.hex_map = None
    self.models = None
    self.processing_model = None
    self.orig_columns = []
    self.preselected = {}

    self.setStyleSheet('QWidget {font-family: "Trebuchet MS"; font-size: 13pt;}')
    self.btnBrowseCsv.clicked.connect(self.read_data_csv)
    self.btnReload.clicked.connect(self.start_over)
    self.tblSummary.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
    self.tblSummary.setSelectionMode(QtWidgets.QTableView.SingleSelection)
    self.tblSummary.itemSelectionChanged.connect(self.item_selected)
    self.btnPrint.clicked.connect(partial(self.send_to_printer))
    self.btnFlash.clicked.connect(self.burn)
    self.txtEvents.setReadOnly(True)

    self.load_config()
    self.populate_hex_map()
    self.autoload_models()
    self.populate_open_ports()
    self.showMaximized()

  def load_config(self):
    config = pd.read_csv(os.path.join(self.base_path, 'config.csv'))
    config = config.to_dict('records')

    config_dict = {}
    for config_item in config:
      config_dict[config_item['param']] = config_item['value']

    self.ctx.config = config_dict

  def autoload_models(self):
    filename = self.ctx.config.get('model_file', None)
    if filename:
      filename = os.path.join(self.base_path, filename)
      self.read_data_csv(filename)

  def populate_open_ports(self):
    ports = get_com_ports()
    if not ports:
      self.show_message('No COM ports discovered.', 'error')
      sys.exit(0)
    self.cbPortsBurner.addItems(ports)
    self.cbPortsPrinter.addItems(ports)

  def populate_hex_map(self):
    data = pd.read_csv(os.path.join(self.base_path, 'hex_map.csv'))
    self.hex_map = data

  def start_over(self):
    self.preselected = {}
    if self.models is not None:
      filename = self.txtCsvFilename.text()
      self.read_data_csv(filename)

  def select_data_csv(self):
    options = QtWidgets.QFileDialog.Options()
    options |= QtWidgets.QFileDialog.DontUseNativeDialog
    filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select File', '', 'CSV Files (*.csv);;XLSX Files (*.xlsx);;All Files (*)', options=options)
    return filename

  def read_data_csv(self, filename):
    if not filename:
      filename = self.select_data_csv()
      if not filename: return False
    self.txtCsvFilename.setText(filename)
    self.btnReload.setEnabled(True)

    data = pd.read_csv(filename)
    def fill_nans(cols, val):
      values = {}
      for col in cols:
        for var in [col, (f'{col}*')]:
          if var in data.columns.tolist(): values[var] = val
      data.fillna(value=values, inplace=True)
      nans = list(values)
      data[nans] = data[nans].astype(type(val))

    hex_file_cols = [col['sw'] for col in list(self.hex_map.to_dict('records')) if not col in common_bins]
    fill_nans(hex_file_cols, '')
    fill_nans(['burned'], 0)
    fill_nans(['passed_test', 'printed'], -1)

    self.orig_columns = list(data.columns.tolist())
    renamed_columns = {}
    for index, column in enumerate(self.orig_columns):
      if '*' in column:
        renamed_column = column.replace('*', '')
        renamed_columns[column] = renamed_column
    data.rename(columns=renamed_columns, inplace=True)

    self.models = data
    self.persist_data_csv()
    self.log_event('Models loaded from CSV: {0}'.format(filename))
    self.restart_cycle()

  def get_summary_columns(self):
    return [col.replace('*', '') for col in self.orig_columns if '*' in col]

  def load_summary(self):
    summary_columns = list(self.get_summary_columns())
    if not summary_columns: return

    self.tblSummary.setRowCount(0)

    summary_columns = ['id'] + summary_columns
    self.tblSummary.setColumnCount(len(summary_columns))

    colors = {
      '-1': lightgray,
      '0': red,
      '1': green
    }

    for row_index, row in enumerate(self.models[summary_columns].to_dict('records')):
      self.tblSummary.insertRow(row_index)
      self.tblSummary.setRowHidden(row_index, True)

      passed_test = str(row['passed_test'])
      printed = str(row['printed'])

      fg_color = QtCore.Qt.black
      bg_color = lightgray

      all_same = passed_test != '-1' and passed_test == printed
      if all_same:
        bg_color = colors[passed_test]
        fg_color = QtCore.Qt.white

      header = self.tblSummary.horizontalHeader()       
      for col_index, (key, value) in enumerate(row.items()):
        header.setSectionResizeMode(col_index, QtWidgets.QHeaderView.Stretch)
        display_value = str(value)

        if key in bool_cols:
          if display_value.isnumeric():
            display_value = '✓' if value == 1 else '✕'

            bg_color = green if value == 1 else red
            fg_color = QtCore.Qt.white
          elif display_value == '-1':
            display_value = '•'

            fg_color = QtCore.Qt.black
            bg_color = lightgray

        cell = QtWidgets.QTableWidgetItem(display_value)
        cell.setBackground(bg_color)
        cell.setForeground(fg_color)

        self.tblSummary.setItem(row_index, col_index, cell)
        self.tblSummary.setHorizontalHeaderItem(col_index, QtWidgets.QTableWidgetItem(summary_columns[col_index]))

  def item_selected(self):
    self.get_selected_item()
    if self.processing_model is None: return      

    if self.processing_model['passed_test'] != 1:
      self.btnFlash.setEnabled(True)
      self.btnPrint.setEnabled(False)
    elif self.processing_model['printed'] != 1:
      self.btnPrint.setEnabled(True)
      self.btnFlash.setEnabled(False)

  def get_available_models(self, model):
    items = self.models[self.models['model'] == model].to_dict('records')
    available_items = [item for item in items if item['passed_test'] != 1 or item['printed'] != 1]

    items = [item['id'] for item in items]
    available_items = [item['id'] for item in available_items]

    return items, available_items

  def create_model_buttons(self):
    for i in range(self.glModels.count()): self.glModels.itemAt(i).widget().close()

    models = self.models.drop_duplicates('model')['model'].tolist()
    clicked = False

    for index, model in enumerate(models):
      items, available_items = self.get_available_models(model)
      
      btn = QtWidgets.QPushButton('{0}\n{1}/{2}'.format(str(model), len(items) - len(available_items), len(items)))
      btn.clicked.connect(partial(self.model_clicked, model, btn))

      preselected_model = self.preselected.get('model', None)
      if not preselected_model in available_items: preselected_model = None

      if not clicked and ((preselected_model is not None and model == preselected_model) or (preselected_model is None and available_items)):
        clicked = True

        click_signal = signals.Signal()
        click_signal.signaled.connect(partial(lambda b: b.click(), btn))

        t = threading.Timer(0.5, lambda: click_signal.signal({}))
        t.start()
      self.glModels.addWidget(btn, 0, index)

  def model_clicked(self, model, btn):
    items, available_items = self.get_available_models(model)

    id_col_index = self.models.columns.get_loc('id')
    has_selected_item = False

    for row in range(self.tblSummary.rowCount()):
      item_id = int(self.tblSummary.item(row, id_col_index).text())
      item_model = self.models[self.models['id'] == item_id].iloc[0]['model']
      self.tblSummary.setRowHidden(row, model != item_model)

      if model == item_model:
        for col in range(self.tblSummary.columnCount()):
          item = self.tblSummary.item(row, col)
          if not item_id in available_items:
            item.setFlags(QtCore.Qt.NoItemFlags)
            item.setForeground(QtCore.Qt.white)

            dimmedColor = item.background().color()
            dimmedColor.setAlpha(255 * 0.5)
            item.setBackground(dimmedColor)
          else:
            item.setFlags(item.flags() ^ QtCore.Qt.NoItemFlags)
            item.setForeground(QtCore.Qt.black)
            solidColor = item.background().color()
            solidColor.setAlpha(255)
            item.setBackground(solidColor)

        preselected_item = self.preselected.get('id', None)
        if not preselected_item in available_items: preselected_item = None

        if not has_selected_item and ((preselected_item is not None and preselected_item == item_id) or (preselected_item is None and item_id in available_items)):
          self.tblSummary.selectRow(row)
          self.tblSummary.setFocus()
          has_selected_item = True

    for i in range(self.glModels.count()): self.glModels.itemAt(i).widget().setStyleSheet('')
    btn.setStyleSheet('background-color: #0384fc; color: white; border-style: inset; padding-top: 3px; padding-bottom: 3px;')

  def get_selected_item(self):
    id_col_index = self.models.columns.get_loc('id')
    selected_item = self.tblSummary.currentRow()
    selected_item = self.tblSummary.item(selected_item, id_col_index)
    if not selected_item: return False
    self.processing_model = self.models[self.models['id'] == int(selected_item.text())].iloc[0]
    return True

  def burn(self):
    if self.processing_model is None: return

    self.centralwidget.setEnabled(False)
    self.execute_burn()

  def run_command(self, command, stream_signal):
    esp_path = os.path.join(self.base_path, 'esptool_py', 'esptool', 'esptool.py')
    comport = str(self.cbPortsBurner.currentText())

    cmd_list = [esp_path, '--baud', '115200', '--port', comport]
    for part in command.split(' '):
      cmd_list.append(part.replace('.....', ' '))

    try:
      espwrapper.run_command(esp_path, cmd_list, stream_signal)
      return { 'success': True }
    except Exception as ex:
      return { 'success': False, 'data': str(ex) }

  def execute_burn_core(self, command, stream_signal, result_signal):
    if self.chkErase.isChecked():
      self.log_event('Erasing chip...')

      erase_result = self.run_command(f'erase_flash', stream_signal)
      erase_success = erase_result['success'] == True and 'Chip erase completed successfully' in self.txtEvents.toPlainText()
      erase_result['success'] = erase_success

      if erase_success:
        burn_result = self.run_command(command, stream_signal)
        result_signal.signal(burn_result)
      else:
        if not 'data' in erase_result:
          erase_result['data'] = 'Chip erase failed...'
        result_signal.signal(erase_result)
    else:
      self.log_event('Burning model {0}'.format(self.processing_model['id']))
      burn_result = self.run_command(command, stream_signal)
      result_signal.signal(burn_result)

  def execute_burn(self):
    model = self.processing_model
    if model is None: return

    sws = []
    for hex_entry in self.hex_map.to_dict('records'):
      hex = hex_entry['hex']
      is_common = hex_entry['sw'] in common_bins
      if is_common:
        filename = hex_entry['sw']
      else:
        filename = model[hex_entry['sw']]

      if filename != '':
        sw = os.path.join(self.base_path, 'sw', filename)
        sw = sw.replace(' ', '.....')
        sws.append(f'{hex} {sw}')

    sws = ' '.join(sws)
    command = f'--chip esp32 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect {sws}'

    result_signal = signals.Signal()
    result_signal.signaled.connect(self.burn_result)

    stream_signal = signals.Signal()
    def on_stream(data):
      print(data['data'], end='')
      self.log_event(data['data'], False)
    stream_signal.signaled.connect(on_stream)

    self.log_event('――――――――――――――――――')
    t = threading.Thread(target=self.execute_burn_core, args=(command, stream_signal, result_signal))
    t.setDaemon(True)
    t.start()

  def burn_result(self, result):
    model = self.processing_model
    if model is None: return
    success = result['success']

    if success:
      if not 'Hard resetting via RTS pin' in self.txtEvents.toPlainText():
        success = False
        if not 'data' in result:
          result['data'] = 'Error: never received resetting via RTS pin signal...'

    if 'data' in result:
      self.log_event(result['data'])
    self.log_event('――――――――――――――――――')
    self.log_event('Burning model {0} result: {1}'.format(model['id'], 'SUCCESS' if success else 'FAILURE'))

    self.centralwidget.setEnabled(True)

    if success:
      self.update_model(model['id'], 'burned', model['burned'] + 1)
      self.create_model_buttons()
      self.load_summary()
      valid = self.get_inspect_result()
      self.log_event('Inspecting model {0}'.format(model['id']))
      self.inspect_result(valid)
    else:
      self.update_model(model['id'], 'passed_test', '-1')
      self.update_model(model['id'], 'printed', '-1')
      self.restart_cycle()

  def get_inspect_result(self):
    self.centralwidget.setEnabled(False)
    inspectDialog = InspectUI(self)
    inspectDialog.exec_()
    self.centralwidget.setEnabled(True)
    return inspectDialog.result

  def inspect_result(self, valid):
    model = self.processing_model
    if model is None: return

    self.update_model(model['id'], 'passed_test', 1 if valid else 0)
    self.log_event('Inspecting model {0} result: {1}'.format(model['id'], 'PASSED' if valid else 'FAILED'))

    if valid:
      autoprint = self.chkAutoprint.isChecked()
      if autoprint:
        self.send_to_printer()
      else:
        self.btnPrint.setEnabled(True)
    else:
      self.update_model(model['id'], 'printed', '-1')
      self.restart_cycle()

  def update_model(self, id, prop, value):
    self.models.loc[self.models['id'] == id, prop] = value
    self.persist_data_csv()

  def send_to_printer(self):
    model = self.processing_model
    if model is None: return

    comport = str(self.cbPortsPrinter.currentText())
    payload = model['setup_payload']

    self.log_event('Printing model {0}'.format(model['id']))
    success = False
    try:
      printer = SerialPort(comport)
      printer.write(f'{payload}\r\n')
      printer.close()
      success = True
    except:
      pass
    finally:
      self.update_model(model['id'], 'printed', 1 if success else 0)
      self.log_event('Printing model {0} result: {1}'.format(model['id'], 'SUCCESS' if success else 'FAILURE'))
      self.btnPrint.setEnabled(False)
      self.restart_cycle()

  def persist_data_csv(self):
    csv_file = self.txtCsvFilename.text()
    models = self.models.copy()

    models = models.astype(str)
    models = models.replace('-1', '')

    models.columns = self.orig_columns
    models.to_csv(csv_file, index=False)

  def restart_cycle(self):
    if self.processing_model is not None:
      self.preselected = {
        'model': self.processing_model['model'],
        'id': self.processing_model['id']
      }
    else:
      self.preselected = {}
    self.processing_model = None

    self.centralwidget.setEnabled(True)
    self.btnFlash.setEnabled(False)

    self.create_model_buttons()
    self.load_summary()

  def log_event(self, data, newline=True):
    self.txtEvents.insertPlainText(str(data))
    if newline:
      self.txtEvents.append('')
    self.txtEvents.ensureCursorVisible()

  def show_message(self, text, msg_type='information'):
    types = {
      'information': QtWidgets.QMessageBox.Information,
      'error': QtWidgets.QMessageBox.Critical
    }
    msg = QtWidgets.QMessageBox()
    msg.setIcon(types[msg_type])
    msg.setText(text)
    msg.setWindowTitle('PCB Burner')
    msg.exec_()

def init_ui(ctx):
  ui = Ui(ctx)
  ctx.app.exec_()