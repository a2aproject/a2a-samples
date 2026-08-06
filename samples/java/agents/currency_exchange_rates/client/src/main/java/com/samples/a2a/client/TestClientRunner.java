package com.samples.a2a.client;
/// usr/bin/env jbang "$0" "$@" ; exit $?
//DEPS io.github.a2asdk:a2a-java-sdk-client:0.3.2.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-jsonrpc:0.3.2.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-grpc:0.3.2.Final
//DEPS com.fasterxml.jackson.core:jackson-databind:2.15.2
//DEPS io.grpc:grpc-netty-shaded:1.69.1
//SOURCES TestClient.java

/**
 * JBang script to run the A2A TestClient example for the Currency Agent. This
 * script automatically handles the dependencies and runs the client.
 *
 * <p>
 * Prerequisites: - JBang installed (see
 * https://www.jbang.dev/documentation/guide/latest/installation.html) - A
 * running Currency Agent server (see README.md for instructions on setting
 * up the
 * agent)
 *
 * <p>
 * Usage: $ jbang TestClientRunner.java
 *
 * <p>
 * The script will communicate with the Currency Agent server and send the
 * message
 * "how much is 10 USD in INR?" to demonstrate the A2A protocol interaction.
 */
public final class TestClientRunner {

  private TestClientRunner() {
    // this avoids a lint issue
  }

  /**
   * Client entry point.
   * @param args this methode doesn't take into account these args
   */
  public static void main(final String[] args) {
    TestClient.main(args);
  }
}
