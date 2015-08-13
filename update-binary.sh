#!/sbin/sh
# META-INF/com/google/android/update-binary
# This file installs the zip file contents to /system. See make-update-zip.py
# ASSUMPTION about environment: recovery mode where /sbin/sh is present!
#
# Copyright (C) 2015 Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>.

binary_version=$1
status_out=/proc/self/fd/$2
zip_name=$3

# Write data, avoid command injection by removing newlines.
write_status() {
    printf "%s\n" "$(tr -d '\n')" >$status_out
}
ui_print() {
    printf "ui_print %s\n" "$1" | write_status
    # Print newline for non-empty strings.
    [ -z "$1" ] || printf "ui_print \n" | write_status
}
set_progress() {
    printf "set_progress %.2f\n" "$1" | write_status
}

# Do not create world-writable files.
umask 22

set_progress 0.0
ui_print ""
ui_print "Generated with make-update-zip.py script from"
ui_print "https://github.com/Lekensteyn/make-gapps-zip"
ui_print ""

# Check binary version
case $binary_version in
1|2|3)
    ui_print "Proceeding with update"
    ;;
*)
    ui_print "Unsupported updater binary version $binary_version"
    exit 1 ;;
esac

if ! mountpoint -q /system; then
    ui_print "Mounting /system"
    mount /system
    if ! mountpoint -q /system; then
        ui_print "Failed to mount /system!"
        ui_print "You need to install a ROM first!"
        exit 1
    fi
fi

set_progress 0.1
ui_print "Extracting $zip_name to /system"
# overwrite files (-o)
unzip -o "$zip_name" "system/*" -d / | while read line; do
    ui_print "unzip: $line"
done

set_progress 0.9
ui_print "Unmounting /system"
umount /system

set_progress 1.0
ui_print "Update complete!"
sleep 3
