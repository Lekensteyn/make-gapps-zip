#!/usr/bin/env python
"""
Creates an APK file, merging OAT-optimized odex files as needed. Given a package
name, it will look for files

    framework/arm/boot.oat
    priv-app/GoogleServicesFramework/GoogleServicesFramework.apk
    priv-app/GoogleServicesFramework/arm/GoogleServicesFramework.odex

and then this program will:

 1. Deoptimize framework/arm/boot.oat to framework/arm/odex/
 2. Deoptimize GoogleServicesFramework.odex to GoogleServicesFramework.dex
 3. Add GoogleServicesFramework.dex as classes.dex to the APK file.

Given a framework name (such as com.google.android.maps), the files

    framework/arm/boot.oat
    framework/com.google.android.maps.jar
    framework/arm/com.google.android.maps.odex
    etc/permissions/com.google.android.maps.xml

will be looked up and this program will additionally install the XML file.

Set the OAT2DEX environment variable to the location of the oat2dex.jar file
(defaults to the bundled oat2dex.jar file).
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

def detect_arch(dirname):
    # Look for first available architecture (as subdir)
    for arch in architectures:
        arch_path = os.path.join(dirname, arch)
        if os.path.isdir(arch_path):
            return arch
    return None

def find_odex_for_apk(apk_path, arch):
    """
    Given a filename "Foo.apk", look for a matching odex file such as
    "arm/Foo.odex". Return the path to that file.
    """
    dirname, filename = os.path.split(apk_path)
    odex_filename = "%s.odex" % os.path.splitext(filename)[0]

    odex_path = os.path.join(dirname, arch, odex_filename)
    if os.path.exists(odex_path):
        return odex_path

    raise RuntimeError("No .odex file found for %s!" % apk_path)

def odex_to_dex(odex_path, boot_odex_path):
    """
    Converts an .odex file to a .dex file, returning its path on success.
    """
    dex_path = "%s.dex" % os.path.splitext(odex_path)[0]
    # Output directory for the dex file
    cwd = os.path.dirname(odex_path)

    # remove old files first (if any, ignore race condition).
    if os.path.exists(dex_path):
        os.remove(dex_path)

    # Try to create a file. Check for the file existence as the exit code is
    # still 0 even for errors...
    cmd = ["java", "-jar", os.path.abspath(OAT2DEX),
           os.path.abspath(odex_path), os.path.abspath(boot_odex_path)]
    _logger.debug("Executing: %s", cmd)
    output = subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.STDOUT)
    if not os.path.exists(dex_path):
        _logger.debug("Program output: %s", output.decode())
        raise RuntimeError("Failed to convert odex to dex")

    # File is generated! Accept it!
    return dex_path

def add_classes_dex(apk_path, dex_path):
    """
    Adds the file specified by dex_path to an APK file (specified by apk_path).

    For reproducible builds, the timestamp of classes.dex matches
    AndroidManifest.xml (for APK files) or META-INF/MANIFEST.MF (for jar files).
    """
    # Sanity check and timestamp and OS type lookup.
    with zipfile.ZipFile(apk_path) as z:
        if "classes.dex" in z.namelist():
            raise RuntimeError("classes.dex is already in %s!" % apk_path)
        if apk_path.endswith(".jar"):
            xml_zinfo = z.getinfo("META-INF/MANIFEST.MF")
        else:
            xml_zinfo = z.getinfo("AndroidManifest.xml")

    # classes.dex zip entry info, independent of time, OS and Python version.
    zinfo = zipfile.ZipInfo("classes.dex", xml_zinfo.date_time)
    zinfo.compress_type = xml_zinfo.compress_type
    zinfo.create_system = xml_zinfo.create_system
    zinfo.create_version = xml_zinfo.create_version
    zinfo.extract_version = xml_zinfo.extract_version
    data = open(dex_path, "rb").read()

    # Write actual classes.dex.
    with zipfile.ZipFile(apk_path, "a") as z:
        z.writestr(zinfo, data)

def process_apk(apk_path, arch, boot_odex_path):
    # Sanity check...
    ext = os.path.splitext(apk_path)[1][1:]
    if ext not in ("apk", "jar"):
        raise RuntimeError("File %s is not an APK or framework file!" % apk_path)

    # Scan for classes.dex in file list
    file_list = zipfile.ZipFile(apk_path).namelist()
    if "classes.dex" not in file_list:
        # Not found? Try to find odex file...
        odex_path = find_odex_for_apk(apk_path, arch)

        # convert it to a dex file...
        dex_path = odex_to_dex(odex_path, boot_odex_path)

        # and add it as a classes.dex file
        add_classes_dex(apk_path, dex_path)
        _logger.info("Added %s to %s as classes.dex", dex_path, apk_path)

    # Ready!
    _logger.info("%s is ready!", apk_path)

def process_boot(boot_odex_path):
    """
    If the boot odex path does not exist, create it based on ../boot.oat
    (relative to the given path).
    """
    # If the optimized dir cannot be found, try to create it.
    if not os.path.isdir(boot_odex_path):
        # Assume ../arch/odex and find ../arch/boot.oat.
        framework_arch_dir = os.path.dirname(boot_odex_path)
        boot_oat_path = os.path.join(framework_arch_dir, "boot.oat")

        cmd = ["java", "-jar", OAT2DEX, "boot", boot_oat_path]
        _logger.info("Processing boot directory, may take a minute...")
        _logger.debug("Executing: %s", cmd)
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            output = e.output
        if not os.path.exists(boot_odex_path):
            _logger.debug("Program output: %s", output.decode())
            raise RuntimeError("Failed to deoptimize boot.oat")

parser = argparse.ArgumentParser("odex2apk.py", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("-d", "--debug", action="store_true",
    help="Enable verbose debug logging")
parser.add_argument("-a", "--arch",
    help="""
    Set architecture for all APKs (auto-detected from boot path if omitted).
    """)
parser.add_argument("-f", "--framework", dest="framework_path",
    help="""
    Directory that contains (arch)/boot.oat (if omitted, use ../../framework
    relative to the first given APK file).
    """)
parser.add_argument("apk_files", nargs="+",
    help="Paths to APK or framework jar files.")

# TODO: this is ugly, maybe split it...
def detect_paths(apk_file, arch=None, framework_path=None):
    first_apk_dir = os.path.dirname(apk_file)

    # Default to ../../framework/boot relative if not given.
    if not framework_path:
        ext = os.path.splitext(apk_file)[1][1:]
        if ext == "apk":
            # Assume path app/Foo/Foo.apk
            framework_path = os.path.join(first_apk_dir, "..", "..", "framework")
        elif ext == "jar":
            # Assume path framework/com.google.android.maps.jar
            framework_path = first_apk_dir
        else:
            _logger.error("Unknown file, expected apk or jar")
            sys.exit(1)

    # Detect architecture based on the APK files.
    if not arch:
        arch = detect_arch(framework_path)
        if not arch:
            _logger.error("Cannot detect architecture")
            sys.exit(1)

    # Assumed boot path, could be non-existing and be created later.
    boot_odex_path = os.path.join(framework_path, arch, "odex")

    return arch, boot_odex_path

def main():
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
            format="%(name)s: %(message)s")

    arch, boot_odex_path = detect_paths(args.apk_files[0],
            args.arch, args.framework_path)

    # Validate boot path and try to optimize these files (needed for APK steps).
    process_boot(boot_odex_path)

    for file_path in args.apk_files:
        try:
            process_apk(file_path, arch, boot_odex_path)
        except:
            _logger.exception("Failed to process %s", file_path)
            sys.exit(1)

if __name__ == "__main__":
    main()
