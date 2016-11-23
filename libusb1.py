import warnings
warnings.warn(
  'Importing this module should not be needed, everything intended to be '
  'exposed should be available in usb1 module.',
  DeprecationWarning,
)
del warnings
from usb1.libusb1 import *
