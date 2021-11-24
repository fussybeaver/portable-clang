#!/usr/bin/env bash

# Script used in CI to build a single configuration of glibc.

set -ex

COMPILER=$1
GLIBC=$2

mkdir -p build
chmod 777 build

docker run \
  -t \
  --rm \
  -v $(pwd)/build:/out \
  -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
  -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
  -e SCCACHE_BUCKET=${SCCACHE_BUCKET} \
  -e SCCACHE_S3_USE_SSL=1 \
  -e SCCACHE_IDLE_TIMEOUT=0 \
  portable-clang:glibc \
  docker-glibc-build.sh ${COMPILER} ${GLIBC}

tar -C build -cvf glibc-${GLIBC}.tar.zst --zstd .
