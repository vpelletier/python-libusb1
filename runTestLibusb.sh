#!/bin/bash
# Run tests against multiple libusb versions.
# Useful to check backward-compatibility with libusb versions which lack some
# exports.
if [ $# -lt 3 ]; then
  echo "Usage: $0 remote remote_name changeset [changeset [...]]"
  exit 1
fi

set -e

base="$PWD/test-libusb"
build_base="$base/build"

remote="$1"
remote_name="$2"
shift 2
repo_dir="${base}/repo/${remote_name}"
test -e "$repo_dir" || git clone -n "$remote" "$repo_dir"
cd "$repo_dir"
# Also test against system-installed libusb
lib_dir_list=("")
# Build all first, test later, so errors are all visible at the end
while [ $# -ne 0 ]; do
  changeset="$1"
  shift
  build_dir="${build_base}/${remote_name}/${changeset}"
  if test ! -e "$build_dir"; then
    mkdir -p "$build_dir"
    git checkout --force "$changeset"
    git clean --force -dx
    ./autogen.sh --prefix="$build_dir"
    make
    make install
  fi
  lib_dir_list+=("${build_dir}/lib")
done

result=0
for lib_dir in "${lib_dir_list[@]}"; do
  export LD_LIBRARY_PATH="${lib_dir}"
  if python -m usb1.testUSB1; then
    :
  else
    echo "status=$?"
    result=1
  fi
done
exit $result
