import IPython.display

from . import taxonomy

def list_code(filename):
    return IPython.display.Code(filename=filename)