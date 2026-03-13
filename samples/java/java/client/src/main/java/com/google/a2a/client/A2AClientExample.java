package com.google.a2a.client;

import com.google.a2a.model.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * Example usage of A2A client - AI Translation Bot
 */
public class A2AClientExample {
    
    public static void main(String[] args) {
        // Create client
        A2AClient client = new A2AClient("http://localhost:8080");
        
        try {
            // Example 1: Get agent card
            System.out.println("=== Getting Translation Bot Agent Card ===");
            AgentCard agentCard = client.getAgentCard();
            System.out.println("Agent: " + agentCard.name());
            System.out.println("Description: " + agentCard.description());
            System.out.println("Version: " + agentCard.version());
            System.out.println("Skills: " + agentCard.skills());
            System.out.println();
            
            // Example 2: Translate French to Chinese
            System.out.println("=== Translating French to Chinese ===");
            
            // Create text part for French to Chinese translation
            TextPart frenchToChinesePart = new TextPart("Bonjour le monde! Comment allez-vous?", null);
            
            Message frenchToChineseMessage = new Message(
                UUID.randomUUID().toString(),  // messageId
                "message",                     // kind
                "user",                        // role
                List.of(frenchToChinesePart), // parts
                null,                         // contextId
                null,                         // taskId
                null,                         // referenceTaskIds
                null                          // metadata
            );
            
            TaskSendParams frenchToChineseParams = new TaskSendParams(
                "french-to-chinese-task",
                null,  // sessionId
                frenchToChineseMessage,
                null,  // pushNotification
                null,  // historyLength
                Map.of()  // metadata
            );
            
            JSONRPCResponse frenchToChineseResponse = client.sendTask(frenchToChineseParams);
            Task frenchToChineseTask = (Task) frenchToChineseResponse.result();
            System.out.println("Original French: " + frenchToChinesePart.text());
            System.out.println("Task ID: " + frenchToChineseTask.id());
            System.out.println("Translation Status: " + frenchToChineseTask.status().state());
            
            // Print translation result if available in history
            if (frenchToChineseTask.history() != null && frenchToChineseTask.history().size() > 1) {
                Message lastMessage = frenchToChineseTask.history().get(frenchToChineseTask.history().size() - 1);
                if (lastMessage.role().equals("assistant") && !lastMessage.parts().isEmpty()) {
                    Part translationPart = lastMessage.parts().get(0);
                    if (translationPart instanceof TextPart textPart) {
                        System.out.println("Chinese Translation: " + textPart.text());
                    }
                }
            }
            System.out.println();
            
            // Example 3: Translate Chinese to English
            System.out.println("=== Translating Chinese to English ===");
            
            TextPart chineseTextPart = new TextPart("你好，世界！欢迎使用AI翻译机器人。", null);
            
            Message chineseMessage = new Message(
                UUID.randomUUID().toString(),  // messageId
                "message",                     // kind
                "user",                        // role
                List.of(chineseTextPart),     // parts
                null,                         // contextId
                null,                         // taskId
                null,                         // referenceTaskIds
                null                          // metadata
            );
            
            TaskSendParams chineseParams = new TaskSendParams(
                "chinese-to-english-task",
                null,  // sessionId
                chineseMessage,
                null,  // pushNotification
                null,  // historyLength
                Map.of()  // metadata
            );
            
            JSONRPCResponse chineseResponse = client.sendTask(chineseParams);
            Task chineseTask = (Task) chineseResponse.result();
            System.out.println("Original Chinese: " + chineseTextPart.text());
            System.out.println("Task ID: " + chineseTask.id());
            System.out.println("Translation Status: " + chineseTask.status().state());
            
            // Print translation result if available in history
            if (chineseTask.history() != null && chineseTask.history().size() > 1) {
                Message lastMessage = chineseTask.history().get(chineseTask.history().size() - 1);
                if (lastMessage.role().equals("assistant") && !lastMessage.parts().isEmpty()) {
                    Part translationPart = lastMessage.parts().get(0);
                    if (translationPart instanceof TextPart textPart) {
                        System.out.println("English Translation: " + textPart.text());
                    }
                }
            }
            System.out.println();
            
            // Example 4: Translate with streaming (French to English)
            System.out.println("=== Streaming Translation (French to English) ===");
            
            TextPart frenchTextPart = new TextPart("Bonjour le monde! Comment allez-vous?", null);
            Message frenchMessage = new Message(
                UUID.randomUUID().toString(),
                "message",
                "user",
                List.of(frenchTextPart),
                null, null, null, null
            );
            
            TaskSendParams frenchParams = new TaskSendParams(
                "french-streaming-task",
                null,  // sessionId
                frenchMessage,
                null,  // pushNotification
                null,  // historyLength
                Map.of()  // metadata
            );
            
            CountDownLatch streamingLatch = new CountDownLatch(1);
            System.out.println("Original French: " + frenchTextPart.text());
            
            client.sendTaskStreaming(frenchParams, new StreamingEventListener() {
                @Override
                public void onEvent(Object event) {
                    System.out.println("Streaming translation event: " + event);
                }
                
                @Override
                public void onError(Exception exception) {
                    System.err.println("Translation streaming error: " + exception.getMessage());
                    streamingLatch.countDown();
                }
                
                @Override
                public void onComplete() {
                    System.out.println("Translation streaming completed");
                    streamingLatch.countDown();
                }
            });
            
            // Wait for streaming to complete
            if (streamingLatch.await(30, TimeUnit.SECONDS)) {
                System.out.println("Streaming translation finished successfully");
            } else {
                System.out.println("Translation streaming timed out");
            }
            System.out.println();
            
            // Example 5: Get task status for translation
            System.out.println("=== Getting Translation Task Status ===");
            TaskQueryParams queryParams = new TaskQueryParams(frenchToChineseTask.id(), Map.of(), null);
            JSONRPCResponse getResponse = client.getTask(queryParams);
            Task retrievedTask = (Task) getResponse.result();
            System.out.println("Retrieved translation task: " + retrievedTask.id());
            System.out.println("Final status: " + retrievedTask.status().state());
            System.out.println();
            
            // Example 6: Cancel a translation task
            System.out.println("=== Canceling Translation Task ===");
            
            TextPart cancelTextPart = new TextPart("Diese Übersetzung wird abgebrochen.", null); // German
            Message cancelMessage = new Message(
                UUID.randomUUID().toString(),
                "message",
                "user",
                List.of(cancelTextPart),
                null, null, null, null
            );
            
            TaskSendParams cancelParams = new TaskSendParams(
                "german-cancel-task",
                null,  // sessionId
                cancelMessage,
                null,  // pushNotification
                null,  // historyLength
                Map.of()  // metadata
            );
            
            // Send task to be canceled
            JSONRPCResponse cancelResponse = client.sendTask(cancelParams);
            Task cancelTask = (Task) cancelResponse.result();
            System.out.println("German text to translate: " + cancelTextPart.text());
            System.out.println("Translation task to cancel: " + cancelTask.id());
            
            // Cancel the task
            TaskIDParams cancelTaskParams = new TaskIDParams(cancelTask.id(), Map.of());
            JSONRPCResponse cancelResult = client.cancelTask(cancelTaskParams);
            Task canceledTask = (Task) cancelResult.result();
            System.out.println("Task canceled: " + canceledTask.id());
            System.out.println("Final status: " + canceledTask.status().state());
            
        } catch (A2AClientException e) {
            System.err.println("A2A Translation Client Error: " + e.getMessage());
            if (e.getErrorCode() != null) {
                System.err.println("Error Code: " + e.getErrorCode());
            }
            e.printStackTrace();
        } catch (Exception e) {
            System.err.println("Unexpected translation error: " + e.getMessage());
            e.printStackTrace();
        }
    }
} 