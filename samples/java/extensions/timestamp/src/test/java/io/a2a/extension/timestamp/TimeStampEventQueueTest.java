package io.a2a.extension.timestamp;

import static io.a2a.extension.timestamp.TimeStampAgentExecutorWrapper.TIMESTAMP_FIELD;
import static io.a2a.extension.timestamp.TimeStampAgentExecutorWrapper.URI;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import io.a2a.server.events.EventQueue;
import io.a2a.spec.Artifact;
import io.a2a.spec.Event;
import io.a2a.spec.Message;
import io.a2a.spec.Message.Role;
import io.a2a.spec.Task;
import io.a2a.spec.TaskArtifactUpdateEvent;
import io.a2a.spec.TaskState;
import io.a2a.spec.TaskStatus;
import io.a2a.spec.TaskStatusUpdateEvent;
import io.a2a.spec.TextPart;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

public class TimeStampEventQueueTest {

    private EventQueue delegateQueue;
    private TimeStampEventQueue timestampQueue;

    @BeforeEach
    public void setUp() {
        delegateQueue = mock(EventQueue.class);
        timestampQueue = new TimeStampEventQueue(delegateQueue);
    }

    @Test
    public void testEnqueueEvent_delegatesEvent() {
        Event event = mock(Event.class);

        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(any(Event.class));
    }

    @Test
    public void testProcessMessage_withNullMetadataAndExtensions() {
        Message message = new Message.Builder()
                .role(Role.USER)
                .parts(List.of(new TextPart("test message")))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(message);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Message processedMessage = (Message) eventCaptor.getValue();

        assertNotNull(processedMessage.getMetadata());
        assertTrue(processedMessage.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertNotNull(processedMessage.getMetadata().get(TIMESTAMP_FIELD));
        assertTrue(processedMessage.getMetadata().get(TIMESTAMP_FIELD) instanceof OffsetDateTime);

        assertNotNull(processedMessage.getExtensions());
        assertTrue(processedMessage.getExtensions().contains(URI));
    }

    @Test
    public void testProcessMessage_withEmptyMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        List<String> extensions = new ArrayList<>();

        Message message = new Message.Builder()
                .role(Role.USER)
                .parts(List.of(new TextPart("test message")))
                .metadata(metadata)
                .extensions(extensions)
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(message);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Message processedMessage = (Message) eventCaptor.getValue();

        assertTrue(processedMessage.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertTrue(processedMessage.getExtensions().contains(URI));
    }

    @Test
    public void testProcessMessage_withExistingMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("existing", "value");
        List<String> extensions = new ArrayList<>();
        extensions.add("existing-extension");

        Message message = new Message.Builder()
                .role(Role.USER)
                .parts(List.of(new TextPart("test message")))
                .metadata(metadata)
                .extensions(extensions)
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(message);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Message processedMessage = (Message) eventCaptor.getValue();

        assertTrue(processedMessage.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertTrue(processedMessage.getMetadata().containsKey("existing"));
        assertTrue(processedMessage.getExtensions().contains(URI));
        assertTrue(processedMessage.getExtensions().contains("existing-extension"));
    }

    @Test
    public void testProcessMessage_withExistingTimestamp() {
        OffsetDateTime existingTimestamp = OffsetDateTime.now();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put(TIMESTAMP_FIELD, existingTimestamp);
        List<String> extensions = new ArrayList<>();
        extensions.add(URI);

        Message message = new Message.Builder()
                .role(Role.USER)
                .parts(List.of(new TextPart("test message")))
                .metadata(metadata)
                .extensions(extensions)
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(message);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Message processedMessage = (Message) eventCaptor.getValue();

        assertEquals(existingTimestamp, processedMessage.getMetadata().get(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTask_withNullMetadata() {
        Task task = new Task.Builder()
                .id("test task")
                .contextId("context-id")
                .status(new TaskStatus(TaskState.COMPLETED))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(task);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Task processedTask = (Task) eventCaptor.getValue();

        assertNotNull(processedTask.getMetadata());
        assertTrue(processedTask.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertNotNull(processedTask.getMetadata().get(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTask_withExistingMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("existing", "value");

        Task task = new Task.Builder()
                .id("test task")
                .contextId("context-id")
                .metadata(metadata)
                .status(new TaskStatus(TaskState.COMPLETED))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(task);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Task processedTask = (Task) eventCaptor.getValue();

        assertTrue(processedTask.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertTrue(processedTask.getMetadata().containsKey("existing"));
    }

    @Test
    public void testProcessTask_withExistingTimestamp() {
        OffsetDateTime existingTimestamp = OffsetDateTime.now();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put(TIMESTAMP_FIELD, existingTimestamp);

        Task task = new Task.Builder()
                .id("test task")
                .contextId("context-id")
                .metadata(metadata)
                .status(new TaskStatus(TaskState.COMPLETED))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(task);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        Task processedTask = (Task) eventCaptor.getValue();

        assertEquals(existingTimestamp, processedTask.getMetadata().get(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTaskStatusUpdateEvent_withNullMetadata() {
        TaskStatusUpdateEvent event = new TaskStatusUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .status(new TaskStatus(TaskState.COMPLETED))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskStatusUpdateEvent processedEvent = (TaskStatusUpdateEvent) eventCaptor.getValue();

        assertNotNull(processedEvent.getMetadata());
        assertTrue(processedEvent.getMetadata().containsKey(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTaskStatusUpdateEvent_withExistingMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("existing", "value");

        TaskStatusUpdateEvent event = new TaskStatusUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .metadata(metadata)
                .status(new TaskStatus(TaskState.COMPLETED))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskStatusUpdateEvent processedEvent = (TaskStatusUpdateEvent) eventCaptor.getValue();

        assertTrue(processedEvent.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertTrue(processedEvent.getMetadata().containsKey("existing"));
    }

    @Test
    public void testProcessTaskStatusUpdateEvent_withExistingTimestamp() {
        OffsetDateTime existingTimestamp = OffsetDateTime.now();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put(TIMESTAMP_FIELD, existingTimestamp);

        TaskStatusUpdateEvent event = new TaskStatusUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .metadata(metadata)
                .status(new TaskStatus(TaskState.COMPLETED))
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskStatusUpdateEvent processedEvent = (TaskStatusUpdateEvent) eventCaptor.getValue();

        assertEquals(existingTimestamp, processedEvent.getMetadata().get(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTaskArtifactUpdateEvent_withNullMetadata() {
        TaskArtifactUpdateEvent event = new TaskArtifactUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .append(false)
                .artifact(new Artifact.Builder()
                        .artifactId("artifact-id")
                        .description("Test artifact")
                        .name("Artifact")
                        .parts(List.of(new TextPart("test message")))
                        .build())
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskArtifactUpdateEvent processedEvent = (TaskArtifactUpdateEvent) eventCaptor.getValue();

        assertNotNull(processedEvent.getMetadata());
        assertTrue(processedEvent.getMetadata().containsKey(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTaskArtifactUpdateEvent_withExistingMetadata() {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("existing", "value");

        TaskArtifactUpdateEvent event = new TaskArtifactUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .append(false)
                .metadata(metadata)
                .artifact(new Artifact.Builder()
                        .artifactId("artifact-id")
                        .description("Test artifact")
                        .name("Artifact")
                        .parts(List.of(new TextPart("test message")))
                        .build())
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskArtifactUpdateEvent processedEvent = (TaskArtifactUpdateEvent) eventCaptor.getValue();

        assertTrue(processedEvent.getMetadata().containsKey(TIMESTAMP_FIELD));
        assertTrue(processedEvent.getMetadata().containsKey("existing"));
    }

    @Test
    public void testProcessTaskArtifactUpdateEvent_withExistingTimestamp() {
        OffsetDateTime existingTimestamp = OffsetDateTime.now();
        Map<String, Object> metadata = new HashMap<>();
        metadata.put(TIMESTAMP_FIELD, existingTimestamp);

        TaskArtifactUpdateEvent event = new TaskArtifactUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .append(false)
                .metadata(metadata)
                .artifact(new Artifact.Builder()
                        .artifactId("artifact-id")
                        .description("Test artifact")
                        .name("Artifact")
                        .parts(List.of(new TextPart("test message")))
                        .build())
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskArtifactUpdateEvent processedEvent = (TaskArtifactUpdateEvent) eventCaptor.getValue();

        assertEquals(existingTimestamp, processedEvent.getMetadata().get(TIMESTAMP_FIELD));
    }

    @Test
    public void testProcessTaskArtifactUpdateEvent_withArtifact() {
        Map<String, Object> artifactMetadata = new HashMap<>();
        List<String> extensions = new ArrayList<>();

        Artifact artifact = new Artifact.Builder()
                .artifactId("artifact-id")
                .parts(List.of(new TextPart("test part")))
                .metadata(artifactMetadata)
                .extensions(extensions)
                .build();

        Map<String, Object> metadata = new HashMap<>();

        TaskArtifactUpdateEvent event = new TaskArtifactUpdateEvent.Builder()
                .taskId("task-1")
                .contextId("context-1")
                .append(false)
                .artifact(artifact)
                .metadata(metadata)
                .build();

        ArgumentCaptor<Event> eventCaptor = ArgumentCaptor.forClass(Event.class);
        timestampQueue.enqueueEvent(event);

        verify(delegateQueue).enqueueEvent(eventCaptor.capture());
        TaskArtifactUpdateEvent processedEvent = (TaskArtifactUpdateEvent) eventCaptor.getValue();

        assertTrue(processedEvent.getMetadata().containsKey(TIMESTAMP_FIELD));

        // Verify artifact was processed
        assertNotNull(processedEvent.getArtifact());
        assertTrue(processedEvent.getArtifact().metadata().containsKey(TIMESTAMP_FIELD));
        assertTrue(processedEvent.getArtifact().extensions().contains(URI));
    }

    @Test
    public void testUnknownEventType_passesThrough() {
        Event unknownEvent = mock(Event.class);

        timestampQueue.enqueueEvent(unknownEvent);

        verify(delegateQueue).enqueueEvent(unknownEvent);
    }

    @Test
    public void testAwaitQueuePollerStart() throws InterruptedException {
        timestampQueue.awaitQueuePollerStart();

        verify(delegateQueue).awaitQueuePollerStart();
    }

    @Test
    public void testClose() {
        timestampQueue.close();

        verify(delegateQueue).close();
    }

    @Test
    public void testCloseWithImmediate() {
        timestampQueue.close(true);

        verify(delegateQueue).close(true);
    }

    @Test
    public void testCloseWithImmediateAndNotifyParent() {
        timestampQueue.close(true, true);

        verify(delegateQueue).close(true, true);
    }

    @Test
    public void testSignalQueuePollerStarted() {
        timestampQueue.signalQueuePollerStarted();

        verify(delegateQueue).signalQueuePollerStarted();
    }

    @Test
    public void testTap() {
        EventQueue tappedQueue = timestampQueue.tap();

        assertEquals(timestampQueue, tappedQueue);
    }
}
