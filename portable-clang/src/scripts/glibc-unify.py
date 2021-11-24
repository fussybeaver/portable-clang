#!/usr/bin/env python3

# Unifies glibc installs in a given directory.

import argparse
import collections
import hashlib
import os
import pathlib
import shutil
import stat
import sys

# 2021-01-01T00:00:00Z
NORMALIZED_TIME = 1609502400


def unify_glibc(
    source_dir: pathlib.Path, dest_dir: pathlib.Path, headers_only: bool = False
):
    """Unifies a multi-arch glibc directory tree.

    The output directory will be a copy of the input directory with
    duplicate files converted to symlinks.
    """
    inputs = [x for x in os.listdir(source_dir) if (source_dir / x).is_dir()]

    digests = collections.defaultdict(set)

    for source in inputs:
        input_path = source_dir / source

        if headers_only:
            input_path = input_path / "usr" / "include"

        for root, dirs, files in os.walk(input_path):
            root = pathlib.Path(root)

            for f in files:
                source_path = root / f
                h = hashlib.sha256()

                # We feed the executable bit into the digest to distinguish between
                # output file modes.
                h.update(b"%d" % (source_path.stat().st_mode & stat.S_IXUSR))

                with source_path.open("rb") as fh:
                    while True:
                        chunk = fh.read(32768)
                        if not chunk:
                            break

                        h.update(chunk)

                digests[h.hexdigest()].add(source_path.relative_to(source_dir))

    # Now rematerialize files in the output directory. Files with multiple instances
    # are symlinks to a shared file. Unique files are regular files.
    os.makedirs(dest_dir, exist_ok=True)

    copy_count = 0
    dedupe_count = 0
    symlink_count = 0

    for digest, files in sorted(digests.items()):
        files = list(sorted(files))

        # Exactly 1 file is a straight file copy.
        if len(files) == 1:
            copy_count += 1

            source_path = source_dir / files[0]
            dest_path = dest_dir / files[0]
            # print("copying %s -> %s" % (source_path, dest_path))
            dest_path.parent.mkdir(0o777, parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            normalize_file(dest_path)

        # Multiple files is a symlink to a common file entry.
        else:
            dedupe_count += 1
            common_rel_path = pathlib.Path("common") / digest[0:2] / digest
            common_path = dest_dir / common_rel_path
            common_path.parent.mkdir(0o777, parents=True, exist_ok=True)

            # Copy the common file into place.
            source_path = source_dir / files[0]
            # print("copying %s -> %s" % (source_path, common_path))
            shutil.copy2(source_path, common_path)
            normalize_file(common_path)

            # Now install all the symlinks.
            for f in files:
                symlink_count += 1

                symlink_source = dest_dir / f
                symlink_source.parent.mkdir(0o777, parents=True, exist_ok=True)

                # The symlink target needs to be relative to the source path so the
                # file layout is portable.
                symlink_target = (
                    "/".join([".."] * (len(f.parents) - 1)) + "/" + str(common_rel_path)
                )
                # print("symlinking %s -> %s" % (symlink_source, symlink_target))
                symlink_source.symlink_to(symlink_target)

    print(
        "copied %d files; symlinked %d files to %d common files"
        % (copy_count, symlink_count, dedupe_count)
    )


def normalize_file(p: pathlib.Path):
    # Normalize permissions.
    if p.stat().st_mode & stat.S_IXUSR:
        p.chmod(0o755)
    else:
        p.chmod(0o644)

    # And atime/mtime.
    os.utime(p, (NORMALIZED_TIME, NORMALIZED_TIME))


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--headers-only", action="store_true", help="Only process header files"
    )
    parser.add_argument(
        "source_dir", help="Directory where glibc installs are extracted"
    )
    parser.add_argument("dest_dir", help="Directory to write unified glibc")

    args = parser.parse_args(args)

    unify_glibc(
        pathlib.Path(args.source_dir),
        pathlib.Path(args.dest_dir),
        headers_only=args.headers_only,
    )


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:
        print("Error: %s" % e)
        sys.exit(1)
