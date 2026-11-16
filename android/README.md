# SPYI Desk Android (development build)

This is the Android source of the same SPYI Desk frontend used in Home Assistant.

- The WebView starts from an offline packaged copy of `spyi_desk/SPYI_Dashboard.html`; Gradle copies the latest HTML into the app before building.
- Configure the HTTPS URL and personal pairing token inside the app. Never place the token in GitHub.
- HTTP connections, mixed content and WebView debugging are disabled in the release variant.
- GitHub Actions performs an **unsigned** Android release compilation. An unsigned APK **cannot be installed**.
- A stable, securely stored signing keystore and a real Android-device test are required for an installable production APK. Do not commit a private keystore or its passwords.
- Background notifications and secure remote HA/Tailscale access remain release blockers; the APK source is not a finished mobile product.

Build locally with Android Studio (JDK 17, SDK 36, Android Gradle Plugin 8.13.x, Gradle 8.13).
