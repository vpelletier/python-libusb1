# pylint: disable=missing-module-docstring
# pylint: disable=invalid-name
import logging
# pylint: disable=import-error
from PyInstaller.utils.hooks import collect_dynamic_libs
# pylint: enable=import-error

logger = logging.getLogger(__name__)
logger.info("--- libusb1 pyinstaller hook ---")
binaries = collect_dynamic_libs('usb1')

logger.info("Added libusb binaries: %s", binaries)
