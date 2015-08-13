#!/usr/bin/env python
"""
Creates an update.zip for privileged system apps.
"""
__author__ = "Peter Wu"
__email__ = "peter@lekensteyn.nl"
__license__ = "MIT"

import argparse, logging, os, subprocess, tempfile, zipfile
import odex2apk
_logger = logging.getLogger("make-update-zip")

# Path inside zip to place the update binary (do not change!)
UPDATE_BINARY_PATH = "META-INF/com/google/android/update-binary"

# The update-binary program that extracts files is passed three parameters:
# $1: update binary number,
# $2: fd number for status updates,
# $3: filename of .zip file.
# See https://source.android.com/devices/tech/ota/tools.html#update-packages
UPDATE_BINARY = os.path.join(_dirname, "update-binary.sh")

default_packages = """
GoogleLoginService GoogleServicesFramework Phonesky PrebuiltGmsCore
""".split()

def find_files(root, prefix=""):
    dirname = os.path.join(root, prefix)
    for name in os.listdir(dirname):
        relative_path = os.path.join(prefix, name)
        full_path = os.path.join(root, relative_path)
        if os.path.isdir(full_path):
            for item in find_files(root, relative_path):
                yield item
        else:
            yield relative_path

def get_files(rootdir, packages):
    for package in packages:
        appdir = "priv-app"
        apk_dir = os.path.join(rootdir, appdir, package)

        # Add all files (apk, arm/bla.so) except hidden files (dotfiles) and
        # (o)dex files.
        for path in find_files(apk_dir):
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1][1:]
            if filename.startswith(".") or ext in ("dex", "odex"):
                continue
            full_path = os.path.join(apk_dir, path)
            arcname = "system/%s/%s/%s" % (appdir, package, path)
            yield full_path, arcname

parser = argparse.ArgumentParser("make-update-zip.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-o", "--output", metavar="PATH", required=True,
    help="Path to output update zip file.")
parser.add_argument("-d", "--debug", action="store_true",
    help="Enable verbose debug logging")
parser.add_argument("-r", "--rootdir", help="Local path to /system directory")
parser.add_argument("packages", nargs="*", help="Names of extra packages")

def main():
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
            format="%(name)s: %(message)s")
    rootdir = args.rootdir if args.rootdir else ""
    packages = args.packages if args.packages else default_packages
    update_zip = args.output

    apk_files = [] # paths
    zip_files = [] # (path, path_in_zip)
    # Discover files
    for path, dest in get_files(rootdir, packages):
        if path.endswith(".apk"):
            apk_files.append(path)
        zip_files.append((path, dest))

    # Deodex each package.
    for apk_path in apk_files:
        _logger.debug("Deodexing %s", apk_path)
        # TODO check exception
        odex2apk.process_apk(apk_path)

    # Create a zip file.
    with zipfile.ZipFile(update_zip, "w", zipfile.ZIP_DEFLATED) as z:
        # Add updater script
        z.write(UPDATE_BINARY, UPDATE_BINARY_PATH)

        # Add each package and related files to the the zip
        for path, dest in zip_files:
            _logger.info("Adding %s", dest)
            z.write(path, dest)

    # Sign the zip.
    pass # TODO call SignApk.jar

    # Done!
    _logger.info("Update zip %s is ready!", update_zip)

if __name__ == "__main__":
    main()
