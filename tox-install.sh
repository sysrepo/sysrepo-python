#!/bin/sh
# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

set -e

toxdir="$1"
shift 1

prefix="$toxdir/.lib"
src="$toxdir/.src"
build="$toxdir/.build"

download()
{
	url="$1"
	branch="$2"
	dir="$3"
	if which git >/dev/null 2>&1; then
		git clone --single-branch --branch "$branch" --depth 1 \
			"$url.git" "$dir"
	elif which curl >/dev/null 2>&1; then
		mkdir -p "$dir"
		curl -L "$url/archive/$branch.tar.gz" | \
			tar --strip-components=1 -zx -C "$dir"
	elif which wget >/dev/null 2>&1; then
		mkdir -p "$dir"
		wget -O - "$url/archive/$branch.tar.gz" | \
			tar --strip-components=1 -zx -C "$dir"
	else
		echo "ERROR: neither git nor curl nor wget are available" >&2
		exit 1
	fi
}

ly_branch="${LIBYANG_BRANCH:-devel}"
ly_src="${LIBYANG_SRC:-$toxdir/.ly.$ly_branch.src}"
ly_prefix="$toxdir/.ly.$ly_branch"
ly_build="$toxdir/.ly.$ly_branch.build"

if ! [ -d "$ly_src" ]; then
	download "https://github.com/CESNET/libyang" "$ly_branch" "$ly_src"
fi

mkdir -p "$ly_build"
cmake -DCMAKE_BUILD_TYPE=debug \
	-DENABLE_BUILD_TESTS=OFF \
	-DENABLE_VALGRIND_TESTS=OFF \
	-DENABLE_CALGRIND_TESTS=OFF \
	-DENABLE_BUILD_FUZZ_TARGETS=OFF \
	-DCMAKE_INSTALL_PREFIX="$ly_prefix" \
	-DCMAKE_INSTALL_LIBDIR=lib \
	-DGEN_LANGUAGE_BINDINGS=OFF \
	-H"$ly_src" -B"$ly_build"

make --no-print-directory -C "$ly_build" -j`nproc`
make --no-print-directory -C "$ly_build" install

ly_prefix=$(readlink -ve $ly_prefix)
export LIBYANG_HEADERS="$ly_prefix/include"
export LIBYANG_LIBRARIES="$ly_prefix/lib"
export LIBYANG_EXTRA_LDFLAGS="-Wl,--enable-new-dtags,-rpath=$LIBYANG_LIBRARIES"

sr_branch="${SYSREPO_BRANCH:-devel}"
sr_src="${SYSREPO_SRC:-$toxdir/.sr.$sr_branch.src}"
sr_prefix="$toxdir/.sr.$sr_branch"
sr_build="$toxdir/.sr.$sr_branch.build"

if ! [ -d "$sr_src" ]; then
	download "https://github.com/sysrepo/sysrepo" "$sr_branch" "$sr_src"
fi

mkdir -p "$sr_build"
cmake -DCMAKE_BUILD_TYPE=debug \
	-DENABLE_TESTS=OFF \
	-DENABLE_BUILD_TESTS=OFF \
	-DENABLE_VALGRIND_TESTS=OFF \
	-DBUILD_EXAMPLES=OFF \
	-DENABLE_COVERAGE=OFF \
	-DGEN_LANGUAGE_BINDINGS=OFF \
	-DCMAKE_INSTALL_PREFIX="$sr_prefix" \
	-DCMAKE_INSTALL_LIBDIR=lib \
	-DLY_HEADER_PATH="$LIBYANG_HEADERS" \
	-DCMAKE_INCLUDE_PATH="$LIBYANG_HEADERS" \
	-DCMAKE_LIBRARY_PATH="$LIBYANG_LIBRARIES" \
	-DCMAKE_SHARED_LINKER_FLAGS="$LIBYANG_EXTRA_LDFLAGS" \
	-H"$sr_src" -B"$sr_build"
make --no-print-directory -C "$sr_build" -j`nproc`
make --no-print-directory -C "$sr_build" install

sr_prefix=$(readlink -ve $sr_prefix)
export SYSREPO_HEADERS="$LIBYANG_HEADERS:$sr_prefix/include"
export SYSREPO_LIBRARIES="$LIBYANG_LIBRARIES:$sr_prefix/lib"
export SYSREPO_EXTRA_LDFLAGS="-Wl,--enable-new-dtags,-rpath=$SYSREPO_LIBRARIES"

# We are building the _libyang.so CFFI module with a custom RPATH. Make sure
# not to store the built .whl file into pip cache directory.
python -m pip install --no-cache-dir "$@"
