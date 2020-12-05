#!/bin/sh -eu
export I_KNOW_HOW_TO_RELEASE_PYTHON_LIBUSB1=1
echo "Fetching libusb1 windows binary distribution..."
python3 setup.py --quiet update_libusb
echo "Building distributions..."
for PYTHON in python2 python3; do
  LIBUSB_BINARY=build/win32/libusb-1.0.dll "${PYTHON}" setup.py --quiet bdist_wheel --plat-name win32
  LIBUSB_BINARY=build/win_amd64/libusb-1.0.dll "${PYTHON}" setup.py --quiet bdist_wheel --plat-name win_amd64
  "${PYTHON}" setup.py --quiet bdist_wheel --plat-name any
done
python3 setup.py --quiet sdist
echo "Done. Next, check their content, sign each:"
echo "  gpg --armor --detach-sign dist/<release file>"
echo "and upload them:"
echo "  twine upload dist/<release file> dist/<release file>.asc"
