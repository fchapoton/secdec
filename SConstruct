# Python packaging has layers upon layers of cruft (setuptools)
# on top of a very simple concept (zip files extracted into the
# site-packages directory). You can read [1,2,3] to get a sense
# of it.
#
# [1] https://blog.schuetze.link/2018/07/21/a-dive-into-packaging-native-python-extensions.html
# [2] https://packaging.python.org/specifications/core-metadata/
# [3] https://www.python.org/dev/peps/pep-0517/
#
# In short:
#
# 1. A source distribution (sdist) is a specially named .tar.gz
#    archive with a special 3-line file PKG-INFO; it can otherwise
#    contain anything.
#
#    This file will be extracted into a temporary location, where
#    it must be able to produce a built distribution.
#
# 2. A build distribution (bdist, aka a wheel) is a specially named
#    .whl (zip) archive with three special files:
#    * <package name>-<package version>.dist-info/WHEEL
#    * <package name>-<package version>.dist-info/METADATA
#    * <package name>-<package version>.dist-info/RECORD
#
#    This whole file will be extracted into site-packages,
#    and the dist-info/RECORD file will be used to keep
#    track of which files belong to which packages.
#
# Therefore, in this SConstruct file we must list every source
# for the sdist, and every binary needed in the bdist. Then,
# SCons will do the rest for us.

import enscons
import os
import toml
import subprocess

def get_universal_platform_tag():
    """Return the wheel tag for universal Python 3, but specific platform."""
    interpreter, abi, platform = enscons.get_binary_tag().split("-")
    return f"py3-none-{platform}"

def DirectoryFiles(dir):
    """Return a File() for each file in and under a directory."""
    files = []
    for root, dirnames, filenames in os.walk(dir):
        files += File(sorted(filenames), root)
    return files

pyproject = toml.load("pyproject.toml")

env = Environment(
    tools = ["default", "packaging", enscons.generate],
    PACKAGE_METADATA = pyproject["tool"]["enscons"],
    WHEEL_TAG = get_universal_platform_tag(),
    ENV = os.environ
)

contrib = SConscript("pySecDecContrib/SConscript", exports="env")
sdist_extra_source = File(Split("""
    COPYING
    ChangeLog
    PKG-INFO
    README.md
    SConstruct
    pyproject.toml
"""))

if os.path.exists(".git"):
    git_id = subprocess.check_output(["git", "rev-parse", "HEAD"], encoding="utf8").strip()
    source = File(subprocess.check_output(["git", "ls-files", "pySecDec"], encoding="utf8").splitlines())
    generated_source = env.Textfile(target="pySecDec/metadata.py", source=[
        f'__version__ = version = "{pyproject["tool"]["enscons"]["version"]}"',
        f'__authors__ = authors = "{pyproject["tool"]["enscons"]["author"]}"',
        f'__commit__ = git_id = "{git_id}"'
    ])
    AlwaysBuild(generated_source)
else:
    # We are in a giless sdist. Lets hope that metadata.py was
    # included in it.
    source = DirectoryFiles("pySecDec")
    generated_source = []

platformlib = env.Whl("platlib", source + generated_source + contrib, root="")
bdist = env.WhlFile(source=platformlib)

# FindSourceFiles() will list every source file of every target
# defined so far.
sdist = env.SDist(source=FindSourceFiles() + generated_source)

env.Alias("sdist", sdist)
env.Alias("dist", sdist + bdist)
env.Alias("build", contrib + generated_source)

env.Default(contrib, sdist, bdist)
