#!/bin/sh
# Build several libusb versions to run tests against.
# Useful to check backward-compatibility with libusb versions which lack some
# exports.
if [ $# -lt 3 ]; then
  echo "Usage: $0 remote remte_name changeset [changeset [...]]"
  exit 1
fi

set -e

BASE="$PWD/test-libusb"
BUILD_BASE="$BASE/build"

REMOTE="$1"
REMOTE_NAME="$2"
shift 2
REPO_DIR="$BASE/repo/$REMOTE_NAME"
mkdir -p "$REPO_DIR"
git clone -n "$REMOTE" "$REPO_DIR"
while [ $# -ne 0 ]; do
  CHANGESET="$1"
  shift
  BUILD_DIR="$BUILD_BASE/$REMOTE_NAME/$CHANGESET"
  mkdir -p "$BUILD_DIR"
  cd "$REPO_DIR"
  git checkout --force "$CHANGESET"
  git clean --force -dx
  ./autogen.sh --prefix="$BUILD_DIR"
  make
  make install
done
