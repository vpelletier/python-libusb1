#!/bin/sh
pylint --disable=locally-disabled,locally-enabled,too-many-lines "$@"
