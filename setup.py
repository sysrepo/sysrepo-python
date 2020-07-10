#!/usr/bin/env python3
# Copyright (c) 2020 6WIND S.A.
# SPDX-License-Identifier: BSD-3-Clause

import datetime
import distutils.file_util
import os
import re
import subprocess

import setuptools
import setuptools.command.sdist


# ------------------------------------------------------------------------------
def git_describe_to_pep440(version):
    """
    ``git describe`` produces versions in the form: `v0.9.8-20-gf0f45ca` where
    20 is the number of commit since last release, and gf0f45ca is the short
    commit id preceded by 'g' we parse this a transform into a pep440 release
    version 0.9.9.dev20 (increment last digit and add dev before 20)
    """
    match = re.search(
        r"""
        v(?P<major>\d+)\.
        (?P<minor>\d+)\.
        (?P<patch>\d+)
        (\.post(?P<post>\d+))?
        (-(?P<dev>\d+))?(-g(?P<commit>.+))?
        """,
        version,
        flags=re.VERBOSE,
    )
    if not match:
        raise ValueError("unknown tag format")
    dic = {
        "major": int(match.group("major")),
        "minor": int(match.group("minor")),
        "patch": int(match.group("patch")),
    }
    fmt = "{major}.{minor}.{patch}"
    if match.group("dev"):
        dic["patch"] += 1
        dic["dev"] = int(match.group("dev"))
        fmt += ".dev{dev}"
    elif match.group("post"):
        dic["post"] = int(match.group("post"))
        fmt += ".post{post}"
    return fmt.format(**dic)


# ------------------------------------------------------------------------------
def get_version_from_archive_id(git_archive_id="$Format:%ct %d$"):
    """
    Extract the tag if a source is from git archive.

    When source is exported via `git archive`, the git_archive_id init value is
    modified and placeholders are expanded to the "archived" revision:

        %ct: committer date, UNIX timestamp
        %d: ref names, like the --decorate option of git-log

    See man gitattributes(5) and git-log(1) (PRETTY FORMATS) for more details.
    """
    # mangle the magic string to make sure it is not replaced by git archive
    if git_archive_id.startswith("$For" "mat:"):
        raise ValueError("source was not modified by git archive")

    # source was modified by git archive, try to parse the version from
    # the value of git_archive_id
    match = re.search(r"tag:\s*v([^,)]+)", git_archive_id)
    if match:
        # archived revision is tagged, use the tag
        return git_describe_to_pep440(match.group(1))

    # archived revision is not tagged, use the commit date
    tstamp = git_archive_id.strip().split()[0]
    d = datetime.datetime.utcfromtimestamp(int(tstamp))
    return d.strftime("%Y.%m.%d.dev0")


# ------------------------------------------------------------------------------
def read_file(fpath, encoding="utf-8"):
    with open(fpath, "r", encoding=encoding) as f:
        return f.read().strip()


# ------------------------------------------------------------------------------
def get_version():
    try:
        return read_file("sysrepo/VERSION")
    except IOError:
        pass

    try:
        return get_version_from_archive_id()
    except ValueError:
        pass

    try:
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--always"], stderr=subprocess.DEVNULL
        )
        return git_describe_to_pep440(out.decode("utf-8").strip())
    except Exception:
        pass

    return "0.0.0"


# ------------------------------------------------------------------------------
class SDistCommand(setuptools.command.sdist.sdist):
    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)
        version_file = os.path.join(base_dir, "sysrepo/VERSION")
        self.execute(
            distutils.file_util.write_file,
            (version_file, [self.distribution.metadata.version]),
            "Writing %s" % version_file,
        )


# ------------------------------------------------------------------------------
setuptools.setup(
    name="sysrepo",
    version=get_version(),
    description="Sysrepo CFFI bindings",
    long_description=read_file("README.rst"),
    license="BSD 3 clause",
    author="Robin Jarry",
    author_email="robin.jarry@6wind.com",
    url="https://www.6wind.com/",
    keywords=["sysrepo", "libyang", "cffi"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
    ],
    packages=["sysrepo"],
    python_requires=">=3.5",
    setup_requires=[
        "setuptools>=40.6.0",
        'cffi; platform_python_implementation != "PyPy"',
    ],
    install_requires=[
        "libyang>=1.4.0",
        'cffi; platform_python_implementation != "PyPy"',
    ],
    cffi_modules=["cffi/build.py:BUILDER"],
    include_package_data=True,
    zip_safe=False,
    cmdclass={"sdist": SDistCommand},
)
