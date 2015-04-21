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

### Apps

Apps in system/priv-app/ are "privileged" apps which can gain more privileges
than other system apps in system/app/ (see [AOSP Privileged vs System app][7]).
Also note that apk files (Shell/Shell.apk) which are deodexed *require* the
corresponding odex file (for example, Shell/arm/Shell.odex). See [What are ODEX
files in Android?][8],

The package names below without `com.` prefix should be prefixed with
`com.google.android.`.

| path under system/priv-app/ | package name | description
| --------------------------- | ------------ | -----------
| AndroidForWork    | androidforwork |
| GCS               | apps.gcs      | Google Connectivity Services (built-in VPN service?).
| GoogleBackupTransport | backuptransport   | Backup your data to Google's server.
| GoogleContacts    | contacts      | Google's replacement for the standard Contacts app.
| GoogleDialer      | dialer        | Google's replacement for the standard Dialer app.
| GoogleFeedback    | feedback      | Submits error reports to Google.
| GoogleLoginService | gsf.login    | Log in with a Google account.
| GoogleOneTimeInitializer | onetimeinitializer | Notifies other Google apps once (Play Store, Camera, Voice Dialer and Google Voice Search).
| GooglePartnerSetup | partnersetup | Collects tracking information (["RLZ"][9]).
| GoogleServicesFramework | gsf     | Required by many apps.
| Hangouts          | talk          | Google Hangouts.
| MusicFX           | com.android.musicfx   | Sound Effects.
| Phonesky          | com.android.vending   | Google Play Store.
| PrebuiltGmsCore   | gms           | Google Play Services.
| SetupWizard       | setupwizard   | Configures device for first time use.
| TagGoogle         | tag           | Google's replacement for [Tag][6] (NFC app)
| Velvet            | googlequicksearchbox  | Google Search and Google Now.
| Wallet            | apps.walletnfcrel     | Google Wallet.

For some reason `system/priv-app/Launcher2/arm/Launcher2.odex` exists without a
matching Launcher2.apk.

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

### Other system files
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
 [9]: https://github.com/rogerta/rlz
 [10]: https://github.com/CyanogenMod/android_device_qcom_common/tree/cm-12.1/power
 [11]: https://github.com/CyanogenMod/android_device_lge_hammerhead/blob/cm-12.0/power/power_hammerhead.c
