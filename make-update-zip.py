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

# Path to signapk.jar for signing the zip file.
# source: https://github.com/android/platform_build/tree/master/tools/signapk
# https://android.googlesource.com/platform/prebuilts/sdk/+archive/master/tools/lib.tar.gz
_dirname = os.path.dirname(__file__)
SIGNAPK = os.getenv("SIGNAPK", os.path.join(_dirname, "signapk.jar"))

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
            # Recurse into directories
            for item in find_files(root, relative_path):
                yield item
        else:
            # Output normal files.
            yield relative_path

def get_files(rootdir, packages):
    for package in packages:
        # Find app dir (priv-app for system apps, app for others), relative to
        # the root directory (system/).
        for appdir in ("priv-app", "app"):
            apk_dir = os.path.join(appdir, package)
            apk_dir_full = os.path.join(rootdir, apk_dir)
            if os.path.isdir(apk_dir_full):
                break

        # Add all files (apk, arm/bla.so) except hidden files (dotfiles) and
        # (o)dex files. Paths are relative to the system/ root.
        for path in find_files(rootdir, apk_dir):
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1][1:]
            if filename.startswith(".") or ext in ("dex", "odex"):
                continue

            full_path = os.path.join(rootdir, path)
            if os.path.islink(full_path):
                # For symlinks, store just the destination.
                target = os.readlink(full_path)
                # Can only handle absolute symlinks in /system/ for now.
                if not target.startswith("/system/"):
                    _logger.warning("Ignoring symlink %s -> %s", relative_path,
                            target)
                    continue
                # TODO store both links and destinations? Current approach will
                # break if the app expects a file in its own directory...
                path = target[len("/system/"):]

            full_path = os.path.join(rootdir, path)
            arcname = "system/%s" % path
            yield full_path, arcname

def make_signed_zip(update_zip, public_key, private_key):
    # Rename the original zip to -unsigned.zip
    source_zip = '%s-unsigned%s' % os.path.splitext(update_zip)
    _logger.debug("Renaming %s to %s", update_zip, source_zip)
    os.rename(update_zip, source_zip)

    # java -jar signapk.jar -w releasekey.{x509.pem,pk8} update{,-signed}.zip
    cmd = ["java", "-jar", SIGNAPK, "-w", public_key, private_key,
            source_zip, update_zip]
    _logger.debug("Executing: %s", cmd)
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        _logger.debug("Program output: %s", e.output.decode())
        _logger.warning("Failed to sign zip, restoring unsigned zip")
        # Failed to create update zip, revert rename
        os.rename(source_zip, update_zip)
        raise

    # Now that the signed zip is available, remove the unsigned one.
    os.remove(source_zip)

parser = argparse.ArgumentParser("make-update-zip.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-f", "--extra-file", dest="extra_files", nargs="*",
    help="""
    Additional files (such as libraries) to include (relative to --rootdir)
    """)
parser.add_argument("-o", "--output", metavar="PATH", required=True,
    help="Path to output update zip file.")
parser.add_argument("-d", "--debug", action="store_true",
    help="Enable verbose debug logging")
parser.add_argument("-c", "--cert", dest="public_key",
    help="X.509 PEM-encoded certificate for signing the zip file")
parser.add_argument("-k", "--key", dest="private_key",
    help="PKCS#8-formatted private key for signing the zip file")
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

    # Add additional files
    for path in args.extra_files:
        zip_files.append((path, path))

    # Pre-processing before APK can be handled.
    arch, boot_odex_path = odex2apk.detect_paths(apk_files[0])
    odex2apk.process_boot(boot_odex_path)

    # Deodex each package.
    for apk_path in apk_files:
        _logger.debug("Deodexing %s", apk_path)
        # TODO check exception
        odex2apk.process_apk(apk_path, arch, boot_odex_path)

    # Create a zip file.
    with zipfile.ZipFile(update_zip, "w", zipfile.ZIP_DEFLATED) as z:
        # Add updater script
        z.write(UPDATE_BINARY, UPDATE_BINARY_PATH)

        # Add each package and related files to the the zip
        for path, dest in zip_files:
            _logger.info("Adding %s", dest)
            z.write(path, dest)

    # Sign the zip if a key is given.
    if args.public_key and args.private_key:
        _logger.info("Created zip %s, trying to sign it...", update_zip)
        make_signed_zip(update_zip, args.public_key, args.private_key)
    else:
        _logger.warn("Zip file %s still needs to be signed!", update_zip)

    # Done!
    _logger.info("Update zip %s is ready!", update_zip)

if __name__ == "__main__":
    main()
