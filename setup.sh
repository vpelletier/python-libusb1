#!/bin/sh
set -eu
# pypy fails when installing the wheel: libusb.py compilation does not produce a .pyc .
for python in /usr/bin/python2.7 /usr/bin/python3.9 /usr/bin/pypy3; do
  "$(dirname "$(realpath "$0")")"/runTestLibusb.sh "$python" https://github.com/libusb/libusb.git libusb.git master v1.0.19 v1.0.22
done
export I_KNOW_HOW_TO_RELEASE_PYTHON_LIBUSB1=1
echo "Fetching libusb1 windows binary distribution..."
python3 setup.py --quiet update_libusb
echo "Building distributions..."
embedded_dll_path="usb1/libusb-1.0.dll"
for python_v in python2 python3; do
  echo "$python_v bdist_wheel win32"
  cp "build/win32/libusb-1.0.dll" "$embedded_dll_path"
  "${python_v}" setup.py --quiet bdist_wheel --plat-name win32 clean --all
  cp "build/win_amd64/libusb-1.0.dll" "$embedded_dll_path"
  "${python_v}" setup.py --quiet bdist_wheel --plat-name win_amd64 clean --all
  rm "$embedded_dll_path"
  "${python_v}" setup.py --quiet bdist_wheel --plat-name any clean --all
done
python3 setup.py --quiet sdist clean --all
release_prefix="dist/libusb1-$(python3 -c 'import versioneer; print(versioneer.get_version())')"
echo "Done. Next, check their content, sign each:"
echo "  for release in ${release_prefix}*; do gpg --armor --detach-sign \"\$release\"; done"
echo "and upload them:"
echo "  twine upload ${release_prefix}*"
