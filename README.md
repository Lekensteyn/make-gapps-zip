# make-gapps-zip
This project tries to inventarize Google Apps for Android ("gapps") and their
dependencies. Finally a script should be made which can create a flashable
update zip from a trusted firmware file.

The base trusted firmware file is
https://developers.google.com/android/nexus/images

## Tool
Some helper tools were created for the purpose of creating an update.zip that
contains APKs and other related files. Almost all of these files are released
under the MIT license (see the header of the files). Exceptions are the binary
jar files, see the [copyright](copyright) document for more details.

Requires Python 2.7.8 or 3.4.2 or newer due to [Python issue
14315](https://bugs.python.org/14315). If you cannot upgrade, try to edit
/usr/lib/python2.7/zipfile.py (or /usr/lib/python3.4/zipfile.py) and change
`while extra:` to `while len(extra) >= 4:` yourself.

Tested with Python 2.7.10 and 3.4.3 and OpenJDK 1.8.0\_51 on Arch Linux x86\_64.
Tested with a patched Python 2.7.5-5ubuntu3 and 3.4.0-0ubuntu2 and OpenJDK
7u79-2.5.6-0ubuntu1.14.04.1  on Ubuntu 14.04LTS.
It should also run on Windows and OS X though (if not, please fill a bug).

odex2apk.py uses oat2dex.jar from https://github.com/testwhat/SmaliEx. A Java 7
build is included in this repo. make-update-zip.py depends on odex2apk.py and
signapk.jar. See the commit logs of those files for more details.

### odex2apk.py
Convenience script that wraps around @testwhat's fork
(https://github.com/testwhat/SmaliEx) of @JesusFreke's smali. For APKs that are
missing the classes.dex file, it generates that file from odex files (only
suitable for Android 5 (Lollipop) that uses ART!). Invoke with the `--help`
option for verbose usage.

### make-update-zip.py
Script that uses [odex2apk.py](odex2apk.py) to deodex ART-optimized APKs and
puts all package-related files into a flashable zip. The installer script inside
the zip ([update-binary](update-binary.sh)) then basically unpacks the system/
folder to the `/system` partition (after mounting it).

Example invocation to create an update.zip file with the four basic files needed
for Google Play and sync adapters for sharing contacts and calender with Google:

    ./make-update-zip.py -o update.zip \
        -c keys/testkey.x509.pem -k keys/testkey.pk8 \
        -r system GoogleLoginService GoogleServicesFramework Phonesky PrebuiltGmsCore \
        GoogleContactsSyncAdapter CalendarProvider

The certificate (`keys/testkey.x509.pem`) and private key (`keys/testkey.pk8`)
must match the keys that were used to sign the system packages (also known as
platform key). If these `-c ... -k ...` options are omitted, then you still have
to sign the packages yourself using signapk.jar.

The resulting zip file can then be installed in recovery with:

    adb sideload update.zip

Execute `make-update-zip.py --help` for more options.

### Reproducibility
For reproducible builds given the same files and signing keys, you must use the
same Java major version. Otherwise signapk.jar orders the META-INF files
differently and also produces a different manifest file (1.7.0\_79 and 1.7.0\_85
result in the same files, 1.7.0\_79 and 1.8.0\_51 are different).

odex2apk.py uses the same timestamp and OS metadata for classes.dex, based on
AndroidManifest.xml inside the APK file, thereby achieving the same identical
file contents.

make-update-zip.py only produces identical files after signing. While unsigned
files have identical file contents, the metadata may be different between runs
(file modification times and operating system origin).

## Gapps documentation
The following sections document files related to Google apps.

The four required applications for Google Play are:

 - GoogleLoginService
 - GoogleServicesFramework
 - Phonesky
 - PrebuiltGmsCore

### Contents
An update zip contains a `META-INF` directory and other helper files. In the
case of gapps, the only other directory is `system/`.

Directory `META-INF` contains:

| path under META-INF/              | description
| --------------------------------- | ------------------
| CERT.RSA                          | Certificate for verifying the cert.sf signatures.
| MANIFEST.MF                       | Contains hashes for files in the archive.
| CERT.SF                           | Contains signatures for the entries in MANIFEST.MF.
| com/google/android/update-binary  | Executed via *Update zip*, typically Edify.
| com/google/android/updater-script | [Edify][1] script invoked by an appropriate `updater-binary` program.

For details on MANIFEST.MF and CERT.SF, see [How does an .apk files get
signed][2]. The `update-binary` is called by the *Update zip* feature in
Recovery (see [install.cpp][3]). It is typically an Edify program which reads
`updater-script` (see [updater.cpp][4]).

The following files exist in Google's factory image for the Nexus 5 (5.1.0
LMY47I) and not in a CyanogenMod 12.1 build (from source at 2015-04-18).

#### Apps

Apps in system/priv-app/ are "privileged" apps which can gain more privileges
than other system apps in system/app/ (see [AOSP Privileged vs System app][7]).
Also note that apk files (Shell/Shell.apk) which are deodexed *require* the
corresponding odex file (for example, Shell/arm/Shell.odex). See [What are ODEX
files in Android?][8]. Files marked with an \* below are **not** odexed.

| path under system/priv-app/ | package name | description
| --------------------------- | ------------ | -----------
| AndroidForWork    | com.google.android.androidforwork |
| GCS\*             | com.google.android.apps.gcs   | Google Connectivity Services (built-in VPN service?).
| GoogleBackupTransport | com.google.android.backuptransport | Backup your data to Google's server.
| GoogleContacts    | com.google.android.contacts   | Google's replacement for the standard Contacts app.
| GoogleDialer      | com.google.android.dialer     | Google's replacement for the standard Dialer app.
| GoogleFeedback    | com.google.android.feedback   | Submits error reports to Google.
| GoogleLoginService| com.google.android.gsf.login  | Log in with a Google account.
| GoogleOneTimeInitializer | com.google.android.onetimeinitializer | Notifies other Google apps once (Play Store, Camera, Voice Dialer and Google Voice Search).
| GooglePartnerSetup| com.google.android.partnersetup| Collects tracking information (["RLZ"][9]).
| GoogleServicesFramework | com.google.android.gsf  | Required by many apps.
| Hangouts\*        | com.google.android.talk       | Google Hangouts.
| MusicFX           | com.android.musicfx           | Sound Effects.
| Phonesky\*        | com.android.vending           | Google Play Store.
| PrebuiltGmsCore\* | com.google.android.gms        | Google Play Services.
| SetupWizard       | com.google.android.setupwizard| Configures device for first time use.
| TagGoogle         | com.google.android.tag        | Google's replacement for [Tag][6] (NFC app)
| Velvet\*          | com.google.android.googlequicksearchbox | Google Search and Google Now.
| Wallet\*          | com.google.android.apps.walletnfcrel | Google Wallet.

For some reason `system/priv-app/Launcher2/arm/Launcher2.odex` exists without a
matching Launcher2.apk.

Non-system apps do not have to be installed. For completeness, a list of files
in system/app/:

| path under system/app/ | package name     | description
| ---------------------- | ---------------- | -----------
| Books             |  com.google.android.apps.books        |
| BrowserProviderProxy | com.android.browser.provider       |
| CalendarGooglePrebuilt | com.google.android.calendar      |
| Chrome            | com.android.chrome                    | Chrome web browser (uses libs, see below).
| CloudPrint2       | com.google.android.apps.cloudprint    |
| ConfigUpdater     | com.google.android.configupdater      |
| DeskClockGoogle   | com.google.android.deskclock          |
| DMAgent           | com.google.android.apps.enterprise.dmagent |
| Drive             | com.google.android.apps.docs          |
| EditorsDocs       | com.google.android.apps.docs.editors.docs |
| EditorsSheets     | com.google.android.apps.docs.editors.sheets |
| EditorsSlides     | com.google.android.apps.docs.editors.slides |
| FaceLock          | com.android.facelock                  |
| FitnessPrebuilt   | com.google.android.apps.fitness       |
| GoogleCamera      | com.google.android.GoogleCamera       |
| GoogleContactsSyncAdapter | com.google.android.syncadapters.contacts |
| GoogleEars        | com.google.android.ears               |
| GoogleEarth       | com.google.earth                      |
| GoogleHindiIME    | com.google.android.apps.inputmethod.hindi |
| GoogleHome        | com.google.android.launcher           |
| GooglePinyinIME   | com.google.android.inputmethod.pinyin |
| GoogleTTS         | com.google.android.tts                |
| iWnnIME           | jp.co.omronsoft.iwnnime.ml            | Japanese input method (uses libs, see below).
| KoreanIME         | com.google.android.inputmethod.korean |
| LatinImeGoogle    | com.google.android.inputmethod.latin  |
| Maps              | com.google.android.apps.maps          |
| MediaShortcuts    | com.google.android.gallery3d          |
| Music2            | com.google.android.music              |
| Newsstand         | com.google.android.apps.magazines     |
| OmaDmclient       | com.redbend.vdmc                      |
| PartnerBookmarksProvider | com.android.providers.partnerbookmarks |
| Photos            | com.google.android.apps.photos        |
| PlayGames         | com.google.android.play.games         |
| PlusOne           | com.google.android.apps.plus          |
| PrebuiltEmailGoogle | com.google.android.email            |
| PrebuiltExchange3Google | com.google.android.gm.exchange  |
| PrebuiltGmail     | com.google.android.gm                 |
| PrebuiltKeep      | com.google.android.keep               |
| PrebuiltNewsWeather | com.google.android.apps.genie.geniewidget |
| SprintHiddenMenu  | com.lge.SprintHiddenMenu              |
| Street            | com.google.android.street             |
| SunBeam           | com.android.phasebeamorange           |
| talkback          | com.google.android.marvin.talkback    |
| Videos            | com.google.android.videos             |
| WebViewGoogle     | com.google.android.webview            |
| YouTube           | com.google.android.youtube            |

#### Other system files
Data which is installed to the system partition (mounted under `/system`) are
listed below.

| path under system/            | description
| ----------------------------- | -----------
| out/bin/install-recovery.sh   |
| out/recovery-from-boot.p      |
| usr/srec/                     | Speech recognition files (for Google Voice?).
| vendor/lib/libfrsdk.so        | Face Recognition library.
| vendor/media/LMspeed\_508.emd | [for Google Hangouts?][5]
| vendor/media/PFFprec\_600.emd | see LMspeed\_508.emd
| vendor/pittpatt/              | Model files for face recognition.

The `com.google.*.xml` files in `/system/etc/permissions` have only effect if a
corresponding `/system/framework/com.google.*.jar` file exist. Overview of such
files:

| permission xml and framework jar name | description
| ------------------------------------- | -----------
| com.google.android.camera2            |
| com.google.android.dialer.support     |
| com.google.android.maps               |
| com.google.android.media.effects      |
| com.google.widevine.software.drm      |

| path under system/            | description
| ----------------------------- | -----------
| etc/firmware/wcd9320      | Audio chip.
| etc/preferred-apps/google.xml | Sets which apps are triggered by which Google apps.
| etc/sysconfig/google\_build.xml | Sets some feature flags like marking it as a Google-branded phone.
| etc/sysconfig/google.xml | Allows GMS, Play store and Volta to run in powersave.
| etc/updatecmds/google\_generic\_update.txt | Commands to move files associated with base Google packages.
| lib/hw/power.hammerhead.so    | [Hammerhead Power HAL][11] (not needed)
| lib/hw/power.msm8974.so       | [Qualcomm Power HAL][10] (not needed)
| lib/soundfx/libfmas.so        | Some audio effects.
| framework/com.android.nfc\_extras.jar | Empty jar file, why...?
| media/audio/ringtones/RobotsforEveryone.ogg
| media/audio/ringtones/SpagnolaOrchestration.ogg
| media/audio/ui/audio\_end.ogg
| media/audio/ui/audio\_initiate.ogg
| media/audio/ui/NFCFailure.ogg
| media/audio/ui/NFCInitiated.ogg
| media/audio/ui/NFCSuccess.ogg
| media/audio/ui/NFCTransferComplete.ogg
| media/audio/ui/NFCTransferInitiated.ogg
| media/audio/ui/VideoStop.ogg

#### Files under /system/lib/
While most of the files in /system/lib/ are library files, there is an exception
for a certain set of files. These are text files:

 - lib\_dic\_en\_tablet\_USUK.conf.so
 - lib\_dic\_en\_USUK.conf.so
 - lib\_dic\_ja\_JP.conf.so
 - lib\_dic\_morphem\_ja\_JP.conf.so

The `libEnjemailuri.so`, `libennj*.so` and `libnj*.so` files all start and
terminate with the character sequence `NJDC`. These files match:

 - libEnjemailuri.so, libennjcon.so, libennjubase1gb.so, libennjubase1.so,
   libennjubase1us.so, libennjubase2.so, libennjubase3.so, libennjyomi.so,
 - libnjaddress.so, libnjcon.so, libnjemoji.so, libnjexyomi\_plus.so,
   libnjexyomi.so, libnjfzk.so, libnjkaomoji.so, libnjname.so, libnjtan.so,
   libnjubase1.so, libnjubase2.so,

The above sets of files seem to be used by **libiwnn.so** which references the
string `NJDC`. This library is used by [iWnnIME][12] which is an input method
for Japanese. The file `/system/framework/framework-res.apk` also contains a
reference to the string `iwnn`.

| path under lib/       | description
| --------------------- | -----------
| libchrome.2214.89.so  | Used by Chrome app (symlinked from it).
| libchromium\_android\_linker.so | Used by Chrome app (symlinked from it).
| libfacelock\_jni.so   | Used by FaceLock app.
| libfilterpack\_facedetect.so | Used by com.google.android.media.effects.
| libgcam.so            | Used by GoogleCamera app.
| libgcam\_swig\_jni.so | Used by GoogleCamera app.
| libgoogle\_hotword\_jni.so | Guessed: "Ok Google" hotword detection (Search).
| libgoogle\_recognizer\_jni\_l.so | Used by GoogleTTS and GoogleEars.
| libiwnn.so            | Used by the iWnnIME app (see above).
| libjni\_latinimegoogle.so | Used by LatinImeGoogle app.
| liblightcycle.so      | Used by PlusOne and GoogleCamera apps.
| libnativehelper\_compat\_libc++.so | Used by libgcam\_swig\_jni.so (GoogleCamera).
| libpatts\_engine\_jni\_api.so | Used by GoogleTTS app.
| libQSEEComAPI.so      | Qualcomm crypto API (facilitates DRM).
| librefocus.so         | Used by GoogleCamera app.
| libspeexwrapper.so    | Used by GoogleTTS app.
| libvcdecoder\_jni.so  | Used by GoogleEars app.
| libvorbisencoder.so   | Used by GoogleEars app.

### Other resources

 - [G+: Getting Android to be as Stallman-friendly as
   possible](https://plus.google.com/+AlexanderSkwar/posts/PqksGdf9N5u)

 [1]: https://wiki.cyanogenmod.org/w/Doc:_About_Edify
 [2]: https://stackoverflow.com/q/3391585/427545
 [3]: https://github.com/CyanogenMod/android_bootable_recovery/blob/cm-12.1/install.cpp
 [4]: https://github.com/CyanogenMod/android_bootable_recovery/blob/cm-12.1/updater/updater.c
 [5]: http://forum.xda-developers.com/showpost.php?p=42278511
 [6]: https://github.com/CyanogenMod/android_packages_apps_Tag
 [7]: https://stackoverflow.com/a/20104400/427545
 [8]: https://stackoverflow.com/a/10323109/427545
 [9]: https://github.com/rogerta/rlz
 [10]: https://github.com/CyanogenMod/android_device_qcom_common/tree/cm-12.1/power
 [11]: https://github.com/CyanogenMod/android_device_lge_hammerhead/blob/cm-12.0/power/power_hammerhead.c
 [12]: https://play.google.com/store/apps/details?id=jp.co.omronsoft.iwnnime.ml
