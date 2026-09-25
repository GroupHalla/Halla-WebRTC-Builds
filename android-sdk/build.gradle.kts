plugins {
    id("com.android.library")
    id("maven-publish")
}

val sdkVersion = rootProject.file("ANDROID_VERSION").readText().trim()

android {
    namespace = "com.halla.webrtc.audio"
    compileSdk = 34

    defaultConfig {
        minSdk = 26
        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        release { isMinifyEnabled = false }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    publishing {
        singleVariant("release") { withSourcesJar() }
    }
}

dependencies {
    api("io.github.webrtc-sdk:android:144.7559.09")
    testImplementation("junit:junit:4.13.2")
}

afterEvaluate {
    publishing {
        publications {
            create<MavenPublication>("release") {
                from(components["release"])
                groupId = "com.halla.webrtc"
                artifactId = "external-audio-android"
                version = sdkVersion
                pom {
                    name.set("Halla WebRTC Android External Audio SDK")
                    description.set("Public PCM injection API for libwebrtc Android AudioDeviceModule")
                    url.set("https://github.com/GroupHalla/Halla-WebRTC-Builds")
                    licenses {
                        license {
                            name.set("BSD-3-Clause")
                            url.set("https://opensource.org/license/bsd-3-clause/")
                        }
                    }
                }
            }
        }
        repositories {
            maven { url = uri(layout.buildDirectory.dir("repo")) }
        }
    }
}
