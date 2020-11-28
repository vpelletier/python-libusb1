#!/bin/sh -ex

PYTHON=${PYTHON:-python}
VERSION=${VERSION:-1.0.23}

cd $(dirname $0)
wget -nc https://github.com/libusb/libusb/releases/download/v${VERSION}/libusb-${VERSION}.7z -P build
sha256sum build/libusb-${VERSION}.7z

# Windows x86
mkdir -p build/win32
7z e -aoa -obuild/win32 build/libusb-${VERSION}.7z MS32/dll/libusb-1.0.dll
sha256sum build/win32/libusb-1.0.dll
LIBUSB_BINARY=build/win32/libusb-1.0.dll ${PYTHON} setup.py bdist_wheel --plat-name win32

# Windows x86_64
mkdir -p build/win_amd64
7z e -aoa -obuild/win_amd64 build/libusb-${VERSION}.7z MS64/dll/libusb-1.0.dll
sha256sum build/win_amd64/libusb-1.0.dll
LIBUSB_BINARY=build/win_amd64/libusb-1.0.dll ${PYTHON} setup.py bdist_wheel --plat-name win_amd64

# arch-independent (uses OS installation)
${PYTHON} setup.py bdist_wheel --plat-name any
