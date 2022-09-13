#!/bin/bash
SCRIPT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pushd $SCRIPT_DIRECTORY > /dev/null

rm -rf .package sh_ops_bucket.zip

zip sh_ops_bucket.zip sh_ops_bucket.py

popd > /dev/null
