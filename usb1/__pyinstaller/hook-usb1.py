import logging
from PyInstaller.utils.hooks import collect_dynamic_libs

logger = logging.getLogger(__name__)
logger.info("--- libusb1 pyinstaller hook ---")
binaries = collect_dynamic_libs('usb1')

logger.info("Added libusb binaries: %s", binaries)
