import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val signingPropsFile = rootProject.file("key.properties")
val signingProps = Properties()
if (signingPropsFile.exists()) FileInputStream(signingPropsFile).use { signingProps.load(it) }
for ((property, env) in mapOf("storeFile" to "TUNIBIZ_SIGN_STORE", "storePassword" to "TUNIBIZ_SIGN_PASSWORD", "keyAlias" to "TUNIBIZ_SIGN_ALIAS", "keyPassword" to "TUNIBIZ_SIGN_KEY_PASSWORD")) {
    System.getenv(env)?.takeIf { it.isNotBlank() }?.let { signingProps.setProperty(property, it) }
}
val hasReleaseKey = listOf("storeFile", "storePassword", "keyAlias", "keyPassword").all { !signingProps.getProperty(it).isNullOrBlank() }
if (gradle.startParameter.taskNames.any { it.contains("release", ignoreCase = true) } && !hasReleaseKey) {
    throw GradleException("Production signing is required: configure android/key.properties privately.")
}
android {
    signingConfigs {
        if (hasReleaseKey) create("production") {
            storeFile = rootProject.file(signingProps.getProperty("storeFile"))
            storePassword = signingProps.getProperty("storePassword")
            keyAlias = signingProps.getProperty("keyAlias")
            keyPassword = signingProps.getProperty("keyPassword")
        }
    }
    namespace = "tn.tunibiz.tunibiz_mobile"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "tn.tunibiz.tunibiz_mobile"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.findByName("production")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
