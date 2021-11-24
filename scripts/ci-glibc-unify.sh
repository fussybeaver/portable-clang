#!/usr/bin/env bash

# Script used in CI to produce unified glibc archives from per-config source
# archives.

set -ex

ls -al

mkdir glibcs
pushd glibcs

for f in ../*.zst; do
    tar xvf $f
done

popd

python3 scripts/glibc-unify.py glibcs dest-all
tar -C dest-all -cvf glibc-all.tar.zst --zstd .

python3 scripts/glibc-unify.py --headers-only glibcs dest-headers
tar -C dest-headers -cvf glibc-headers.tar.zst --zstd .
