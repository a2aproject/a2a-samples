plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ktlint)
}

dependencies {
    implementation(platform(libs.kotlin.bom))
    implementation(platform(libs.kotlinx.coroutines.bom))

    implementation(libs.koog.agents)
    implementation(libs.koog.agents.features.a2a.server)
    implementation(libs.koog.agents.features.a2a.client)
    implementation(libs.koog.a2a.transport.server.jsonrpc.http)
    implementation(libs.koog.a2a.transport.client.jsonrpc.http)

    implementation(libs.kotlinx.datetime)
    implementation(libs.kotlinx.coroutines.core)

    implementation(libs.ktor.server.cio)

    runtimeOnly(libs.logback.classic)
}

fun registerRunExampleTask(
    name: String,
    mainClassName: String,
) = tasks.register<JavaExec>(name) {
    doFirst {
        standardInput = System.`in`
        standardOutput = System.out
    }

    mainClass.set(mainClassName)
    classpath = sourceSets["main"].runtimeClasspath
}
// Simple joke generation
registerRunExampleTask("runExampleSimpleJokeServer", "ai.koog.example.simplejoke.ServerKt")
registerRunExampleTask("runExampleSimpleJokeClient", "ai.koog.example.simplejoke.ClientKt")

// Advanced joke generation
registerRunExampleTask("runExampleAdvancedJokeServer", "ai.koog.example.advancedjoke.ServerKt")
registerRunExampleTask("runExampleAdvancedJokeClient", "ai.koog.example.advancedjoke.ClientKt")
