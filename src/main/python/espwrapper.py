import importlib.util, sys

def run_command(path, command, signal):
  spec = importlib.util.spec_from_file_location('esptool', path)
  esptool = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(esptool)

  old_args = sys.argv
  sys.argv = command

  try:
    esptool.main(signal)
  except Exception as ex:
    error = ex.args
    if type(error) is tuple:
      if len(error) == 2:
        (data, message) = error
        raise Exception(message)
      else:
        raise Exception(str(error[0]))
    else:
      raise Exception(str(error))
  finally:
    sys.argv = old_args