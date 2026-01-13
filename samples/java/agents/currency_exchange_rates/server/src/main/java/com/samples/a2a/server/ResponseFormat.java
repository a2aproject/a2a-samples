package com.samples.a2a.server;

public record ResponseFormat(Status status, String message) {
  public enum Status {
    /** INPUT_REQUIRED status. */
    INPUT_REQUIRED,
    /** COMPLETED status. */
    COMPLETED,
    /** ERROR status. */
    ERROR
  }
}
