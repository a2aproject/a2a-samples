rootProject.name = "koog"

pluginManagement {
    repositories {
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    @Suppress("UnstableApiUsage")
    repositories {
        mavenCentral()
        google()
        // Public JetBrains repo with dev Koog builds
        maven(url = "https://packages.jetbrains.team/maven/p/grazi/grazie-platform-public")
    }
}
