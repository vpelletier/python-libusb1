#!/bin/bash
# Run tests against multiple libusb versions.
# Useful to check backward-compatibility with libusb versions which lack some
# exports.
set -eu

if [ $# -lt 4 ]; then
  echo "Usage: $0 python remote remote_name changeset [changeset [...]]"
  exit 1
fi
python="$1"
remote="$2"
remote_name="$3"
shift 3

if [ "x$python" = "x" ]; then
  echo "<python> argument must not be empty"
  exit 1
fi

python_libusb1="$(dirname "$(realpath "$0")")"
base="${python_libusb1}/test-libusb"
venv_dir="${base}/$(basename "$python")"
build_base="${base}/build"
repo_dir="${base}/repo/${remote_name}"

test -e "$venv_dir" && rm -r "$venv_dir"
virtualenv --python "$python" "$venv_dir"
"${venv_dir}/bin/pip" install "$python_libusb1"

if [ -e "$repo_dir" ]; then
  git -C "$repo_dir" fetch
else
  git clone --no-checkout "$remote" "$repo_dir"
fi
cd "$repo_dir"
# Also test against system-installed libusb
lib_dir_list=("")
# Build all first, test later, so errors are all visible at the end
while [ $# -ne 0 ]; do
  changeset="$1"
  shift
  build_dir="${build_base}/${remote_name}/${changeset}"
  if [ ! -e "$build_dir" ]; then
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
venv_python="${venv_dir}/bin/python"
for lib_dir in "${lib_dir_list[@]}"; do
  export LD_LIBRARY_PATH="${lib_dir}"
  if "$venv_python" -m usb1.testUSB1; then
    :
  else
    echo "usb1.testUSB1 failed with ${lib_dir}: status=$?"
    result=1
  fi
  if "$venv_python" "${python_libusb1}/examples/listdevs.py"; then
    :
  else
    echo "examples/listdevs.py failed with ${lib_dir}: status=$?"
    result=1
  fi
  if timeout --preserve-status --signal INT 1 "$venv_python" "${python_libusb1}/examples/hotplug.py"; then
    :
  else
    echo "examples/hotplug.py failed with ${lib_dir}: status=$?"
    result=1
  fi
done
exit $result
