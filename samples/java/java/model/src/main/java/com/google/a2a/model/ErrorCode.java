package com.google.a2a.model;

import com.fasterxml.jackson.annotation.JsonValue;

/**
 * ErrorCode represents the error codes used in the A2A protocol
 */
public enum ErrorCode {
    PARSE_ERROR(-32700),
    INVALID_REQUEST(-32600),
    METHOD_NOT_FOUND(-32601),
    INVALID_PARAMS(-32602),
    INTERNAL_ERROR(-32603),
    TASK_NOT_FOUND(-32000),
    TASK_NOT_CANCELABLE(-32001),
    PUSH_NOTIFICATION_NOT_SUPPORTED(-32002),
    UNSUPPORTED_OPERATION(-32003),
    INVALID_AGENT_RESPONSE(-32004),
    CONTENT_TYPE_NOT_SUPPORTED(-32005);

    private final int value;

    ErrorCode(int value) {
        this.value = value;
    }

    @JsonValue
    public int getValue() {
        return value;
    }
} 