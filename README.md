# make-gapps-zip
This project tries to inventarize Google Apps for Android ("gapps") and their
dependencies. Finally a script should be made which can create a flashable
update zip from a trusted firmware file.

The base trusted firmware file is
https://developers.google.com/android/nexus/images

## Contents
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

| path              | description
| ----------------- | -----------
| etc/firmware/wcd9320
| etc/permissions/com.google.android.camera2.xml
| etc/permissions/com.google.android.dialer.support.xml
| etc/permissions/com.google.android.maps.xml
| etc/permissions/com.google.android.media.effects.xml
| etc/permissions/com.google.widevine.software.drm.xml
| lib/hw/power.hammerhead.so
| lib/hw/power.msm8974.so
| lib/soundfx/libfmas.so
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

Apps in system/priv-app/ are "privileged" apps which can gain more privileges
than other system apps in system/app/ (see [AOSP Privileged vs System app][7]).
Also note that apk files (Shell/Shell.apk) which are deodexed *require* the
corresponding odex file (for example, Shell/arm/Shell.odex). See [What are ODEX
files in Android?][8],

| path under system/priv-app/ | description
| --------------------------- | -----------
| AndroidForWork        |
| GCS                   |
| GoogleBackupTransport |
| GoogleContacts        |
| GoogleDialer          | Google's replacement for the stamdard Dialer app.
| GoogleFeedback        |
| GoogleLoginService    |
| GoogleOneTimeInitializer |
| GooglePartnerSetup    |
| GoogleServicesFramework | Required by many apps.
| Hangouts              |
| Launcher2             |
| MusicFX               |
| Phonesky              | Google Play Store.
| PrebuiltGmsCore       |
| SetupWizard           | Apparently important, configures device for first time use.
| TagGoogle             | Google's replacement for [Tag][6] (NFC app)
| Velvet                | Google Search.
| Wallet                | Google Wallet.

Non-system apps do not have to be installed. For completeness, a list of files
in system/app/:

| path under system/app/ | description
| ---------------------- | -----------
| Books                  |
| BrowserProviderProxy   |
| CalendarGooglePrebuilt |
| Chrome                 |
| CloudPrint2            |
| ConfigUpdater          |
| DeskClockGoogle        |
| DMAgent                |
| Drive                  |
| EditorsDocs            |
| EditorsSheets          |
| EditorsSlides          |
| FaceLock               |
| FitnessPrebuilt        |
| GoogleCamera           |
| GoogleContactsSyncAdapter |
| GoogleEars             |
| GoogleEarth            |
| GoogleHindiIME         |
| GoogleHome             |
| GooglePinyinIME        |
| GoogleTTS              |
| iWnnIME                |
| KoreanIME              |
| LatinImeGoogle         |
| Maps                   |
| MediaShortcuts         |
| Music2                 |
| Newsstand              |
| OmaDmclient            |
| PartnerBookmarksProvider |
| Photos                 |
| PlayGames              |
| PlusOne                |
| PrebuiltEmailGoogle    |
| PrebuiltExchange3Google |
| PrebuiltGmail          |
| PrebuiltKeep           |
| PrebuiltNewsWeather    |
| SprintHiddenMenu       |
| Street                 |
| SunBeam                |
| talkback               |
| Videos                 |
| WebViewGoogle          |
| YouTube                |

## Other resources

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
