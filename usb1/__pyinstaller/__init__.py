# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=invalid-name
import os

def get_hook_dirs():
    return [os.path.dirname(__file__)]

def get_PyInstaller_tests():
    return [os.path.dirname(__file__)]
