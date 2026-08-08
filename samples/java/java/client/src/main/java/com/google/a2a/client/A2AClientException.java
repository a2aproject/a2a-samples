package com.google.a2a.client;

/**
 * Exception thrown by A2A client operations
 */
public class A2AClientException extends Exception {
    
    private final Integer errorCode;
    
    public A2AClientException(String message) {
        super(message);
        this.errorCode = null;
    }
    
    public A2AClientException(String message, Throwable cause) {
        super(message, cause);
        this.errorCode = null;
    }
    
    public A2AClientException(String message, Integer errorCode) {
        super(message);
        this.errorCode = errorCode;
    }
    
    public A2AClientException(String message, Integer errorCode, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }
    
    /**
     * Get the A2A error code if available
     */
    public Integer getErrorCode() {
        return errorCode;
    }
} 