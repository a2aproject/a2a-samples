package io.a2a.extension.timestamp;

import static io.a2a.extension.timestamp.TimeStampAgentExecutorWrapper.TIMESTAMP_FIELD;
import static io.a2a.extension.timestamp.TimeStampAgentExecutorWrapper.URI;

import io.a2a.server.events.EventQueue;
import io.a2a.spec.Artifact;
import io.a2a.spec.Event;
import io.a2a.spec.Message;
import io.a2a.spec.Task;
import io.a2a.spec.TaskArtifactUpdateEvent;
import io.a2a.spec.TaskStatusUpdateEvent;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TimeStampEventQueue extends EventQueue {

    private final EventQueue delegate;

    public TimeStampEventQueue(EventQueue delegate) {
        this.delegate = delegate;
    }

    @Override
    public void enqueueEvent(Event event) {
        this.delegate.enqueueEvent(timestampEvent(event));
    }

    private Event timestampEvent(Event event) {
        if (event instanceof Message message) {
            return processMessage(message);
        }
        if (event instanceof TaskArtifactUpdateEvent taskArtifactUpdateEvent) {
            return processTaskArtifactUpdateEvent(taskArtifactUpdateEvent);
        }
        if (event instanceof TaskStatusUpdateEvent taskStatusUpdateEvent) {
            return processTaskStatusUpdateEvent(taskStatusUpdateEvent);
        }
        if (event instanceof Task task) {
            return processTask(task);
        }
        return event;
    }

    private Message processMessage(Message message) {
        Map<String, Object> metadata = message.getMetadata() == null ? new HashMap<>() : new HashMap<>(message.getMetadata());
        if (!metadata.containsKey(TIMESTAMP_FIELD)) {
            metadata.put(TIMESTAMP_FIELD, OffsetDateTime.now(ZoneOffset.UTC));
        }
        List<String> extensions = message.getExtensions() == null ? new ArrayList<>() : new ArrayList<>(message.getExtensions());
        if (!extensions.contains(URI)) {
            extensions.add(URI);
        }
        return new Message.Builder(message).metadata(metadata).extensions(extensions).build();
    }

    private Task processTask(Task task) {
        Map<String, Object> metadata = task.getMetadata() == null ? new HashMap<>() : new HashMap<>(task.getMetadata());
        if (!metadata.containsKey(TIMESTAMP_FIELD)) {
            metadata.put(TIMESTAMP_FIELD, OffsetDateTime.now(ZoneOffset.UTC));
        }  
        List<Artifact> artifacts = new ArrayList<>();
        for (Artifact artifact : task.getArtifacts()) {
            artifacts.add(processArtifact(artifact));
        }
        return new Task.Builder(task).artifacts(artifacts).metadata(metadata).build();
    }

    private TaskStatusUpdateEvent processTaskStatusUpdateEvent(TaskStatusUpdateEvent taskStatusUpdateEvent) {
        Map<String, Object> metadata = taskStatusUpdateEvent.getMetadata() == null ? new HashMap<>() : new HashMap<>(taskStatusUpdateEvent.getMetadata());
        if (!metadata.containsKey(TIMESTAMP_FIELD)) {
            metadata.put(TIMESTAMP_FIELD, OffsetDateTime.now(ZoneOffset.UTC));
        }
        return new TaskStatusUpdateEvent.Builder(taskStatusUpdateEvent).metadata(metadata).build();
    }

    private TaskArtifactUpdateEvent processTaskArtifactUpdateEvent(TaskArtifactUpdateEvent taskArtifactUpdateEvent) {
        Map<String, Object> metadata = taskArtifactUpdateEvent.getMetadata() == null ? new HashMap<>() : new HashMap<>(taskArtifactUpdateEvent.getMetadata());
        if (!metadata.containsKey(TIMESTAMP_FIELD)) {
            metadata.put(TIMESTAMP_FIELD, OffsetDateTime.now(ZoneOffset.UTC));
        }
        if (taskArtifactUpdateEvent.getArtifact() != null) {
            return new TaskArtifactUpdateEvent.Builder(taskArtifactUpdateEvent).artifact(processArtifact(taskArtifactUpdateEvent.getArtifact())).metadata(metadata).build();
        }
        return new TaskArtifactUpdateEvent.Builder(taskArtifactUpdateEvent).metadata(metadata).build();
    }

    private Artifact processArtifact(Artifact artifact) {
        Map<String, Object> metadata = artifact.metadata() == null ? new HashMap<>() : new HashMap<>(artifact.metadata());
        if (!metadata.containsKey(TIMESTAMP_FIELD)) {
            metadata.put(TIMESTAMP_FIELD, OffsetDateTime.now(ZoneOffset.UTC));
        }
        List<String> extensions = artifact.extensions() == null ? new ArrayList<>() : new ArrayList<>(artifact.extensions());
        if (!extensions.contains(URI)) {
            extensions.add(URI);
        }
        return new Artifact.Builder(artifact).metadata(metadata).extensions(extensions).build();
    }

    @Override
    public void awaitQueuePollerStart() throws InterruptedException {
        this.delegate.awaitQueuePollerStart();
    }

    @Override
    public void close() {
        this.delegate.close();
    }

    @Override
    public void close(boolean immediate) {
        this.delegate.close(immediate);
    }

    @Override
    public void close(boolean immediate, boolean notifyParent) {
        this.delegate.close(immediate, notifyParent);
    }

    @Override
    public void signalQueuePollerStarted() {
        this.delegate.signalQueuePollerStarted();
    }

    @Override
    public EventQueue tap() {
        return this;
    }
}
