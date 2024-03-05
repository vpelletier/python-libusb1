#!/bin/bash
set -eu
cd "$(dirname "$(realpath "$0")")"
for python_v in python3 pypy3; do
  if ./runTestLibusb.sh "$python_v" https://github.com/libusb/libusb.git libusb.git master v1.0.19 v1.0.22 v1.0.24 v1.0.25 v1.0.26 v1.0.27; then
    :
  else
    echo "runTestLibusb.sh failed with ${python_v} ($("$python_v" --version))"
    exit 1
  fi
done
export I_KNOW_HOW_TO_RELEASE_PYTHON_LIBUSB1=1
echo "Fetching libusb1 windows binary distribution..."
python3 setup.py --quiet update_libusb
echo "Building distributions..."
embedded_dll_path="usb1/libusb-1.0.dll"
for python_v in python3; do
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
twine check --strict "${release_prefix}"*.{whl,tar.gz}
echo "Done. Next, check their content, sign each:"
echo "  for release in ${release_prefix}-*.whl ${release_prefix}.tar.gz; do gpg --armor --detach-sign \"\$release\"; done"
echo "upload them to pypi:"
echo "  twine upload ${release_prefix}-*.whl{,.asc} ${release_prefix}.tar.gz{,.asc}"
echo "and create a new release on github"
