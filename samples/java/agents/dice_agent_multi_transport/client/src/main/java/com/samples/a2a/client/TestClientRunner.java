///usr/bin/env jbang "$0" "$@" ; exit $?
//DEPS io.github.a2asdk:a2a-java-sdk-client:0.3.0.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-jsonrpc:0.3.0.Final
//DEPS io.github.a2asdk:a2a-java-sdk-client-transport-grpc:0.3.0.Final
//DEPS com.fasterxml.jackson.core:jackson-databind:2.15.2
//DEPS io.grpc:grpc-netty-shaded:1.69.1
//SOURCES TestClient.java

/**
 * JBang script to run the A2A TestClient example for the Dice Agent. This
 * script automatically handles the dependencies and runs the client.
 *
 * <p>
 * Prerequisites: - JBang installed (see
 * https://www.jbang.dev/documentation/guide/latest/installation.html) - A
 * running Dice Agent server (see README.md for instructions on setting up the
 * agent)
 *
 * <p>
 * Usage: $ jbang TestClientRunner.java
 *
 * <p>
 * Or with a custom server URL: $ jbang TestClientRunner.java
 * --server-url=http://localhost:10000
 *
 * <p>
 * The script will communicate with the Dice Agent server and send the message
 * "Can you roll a 5 sided die" to demonstrate the A2A protocol interaction.
 */
public final class TestClientRunner {

    private TestClientRunner() {
        // this avoids a lint issue
    }

    /**
     * Client entry point.
     * @param args can optionally contain the --server-url and --message to use
     */
    public static void main(final String[] args) {
        com.samples.a2a.client.TestClient.main(args);
    }
}
