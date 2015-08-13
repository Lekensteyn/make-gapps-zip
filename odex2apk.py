#!/usr/bin/env python
"""
Creates an APK file, merging OAT-optimized odex files as needed. Given a
directory containing

    GoogleServicesFramework.apk (without classes.dex)
    arm/GoogleServicesFramework.odex

this program create a classes.dex file from arm/GoogleServicesFramework.odex and
put it in the original GoogleServicesFramework.apk file. If a classes.dex file
already exists, no action is taken. (As an implementation detail, the file
arm/GoogleServicesFramework.dex is also created.)

Set the OAT2DEX environment variable to the location of the oat2dex.jar file.
"""
__author__ = "Peter Wu"
__email__ = "peter@lekensteyn.nl"
__license__ = "MIT"

import argparse, sys, zipfile, os, subprocess, logging
_logger = logging.getLogger("odex2apk")

# Path to oat2dex.jar (from https://github.com/testwhat/SmaliEx.git)
# If not set, try to use a jar file next to the file.
_dirname = os.path.dirname(__file__)
OAT2DEX = os.getenv("OAT2DEX", os.path.join(_dirname, "oat2dex.jar"))

# Supported architectures (first match will be used)
architectures = ["arm", "arm64", "x86", "x86_64"]

def find_odex_for_apk(apk_path):
    """
    Given a filename "Foo.apk", look for a matching odex file such as
    "Foo/Foo.odex". Return the path to that file.
    """
    dirname, filename = os.path.split(apk_path)
    odex_filename = "%s.odex" % os.path.splitext(filename)[0]

    # Look for first available architecture
    for arch in architectures:
        odex_path = os.path.join(dirname, arch, odex_filename)
        if os.path.exists(odex_path):
            return odex_path

    raise FileNotFoundError("No .odex file found!")

def odex_to_dex(odex_path):
    """
    Converts an .odex file to a .dex file, returning its path on success.
    """
    dex_path = '%s.dex' % os.path.splitext(odex_path)[0]
    # Output directory for the dex file
    cwd = os.path.dirname(odex_path)

    # remove old files first
    try:
        os.remove(dex_path)
    except FileNotFoundError:
        pass # ignore missing files

    # Try to create a file. Check for the file existence as the exit code is
    # still 0 even for errors...
    cmd = ["java", "-jar", os.path.abspath(OAT2DEX), "odex",
           os.path.abspath(odex_path)]
    _logger.debug('Executing: %s', cmd)
    output = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
    if not os.path.exists(dex_path):
        _logger.debug('Program output: %s', output.decode())
        raise RuntimeError("Failed to convert odex to dex")

    # File is generated! Accept it!
    return dex_path

def add_classes_dex(apk_path, dex_path):
    """
    Adds the file specified by dex_path to an APK file (specified by apk_path).
    """
    with zipfile.ZipFile(apk_path, "a") as z:
        z.write(dex_path, "classes.dex")

def process_apk(apk_path):
    # Sanity check...
    if not apk_path.endswith(".apk"):
        raise RuntimeError("File %s is not an APK file!" % apk_path)

    # Scan for classes.dex in file list
    file_list = zipfile.ZipFile(apk_path).namelist()
    if "classes.dex" not in file_list:
        # Not found? Try to find odex file...
        odex_path = find_odex_for_apk(apk_path)

        # convert it to a dex file...
        dex_path = odex_to_dex(odex_path)

        # and add it as a classes.dex file
        add_classes_dex(apk_path, dex_path)
        _logger.info("Added %s to %s as classes.dex", dex_path, apk_path)

    # Ready!
    _logger.info('%s is ready!', apk_path)

parser = argparse.ArgumentParser("odex2apk.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('-d', '--debug', action='store_true',
    help='Enable verbose debug logging')
parser.add_argument("files", nargs="+", help="Paths to APK files")

def main():
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
            format='%(name)s: %(message)s')
    for file_path in args.files:
        try:
            process_apk(file_path)
        except:
            _logger.exception('Failed to process %s', file_path)
            sys.exit(1)

if __name__ == "__main__":
    main()
