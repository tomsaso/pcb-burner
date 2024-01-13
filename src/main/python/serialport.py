import serial
from serial.tools import list_ports

class SerialPort:
  def __init__(self, port):
    comport = serial.Serial()
    comport.port = port
    comport.baudrate = 9600
    comport.open()
    self.comport = comport

  def write(self, data):
    self.comport.write(data.encode())

  def close(self):
    self.comport.close()

def get_com_ports():
  return sorted([element.device for element in list_ports.comports()])