import {
    Message,
    Task,
} from "../../schema.js";

export class RequestContext {
    public readonly userMessage: Message;
    private cancellationChecker: () => boolean;
    public readonly task?: Task;
    public readonly referenceTasks?: Task[];

    constructor(
        userMessage: Message,
        cancellationChecker: () => boolean,
        task?: Task,
        referenceTasks?: Task[]
    ) {
        this.userMessage = userMessage;
        this.cancellationChecker = cancellationChecker;
        this.task = task;
        this.referenceTasks = referenceTasks;
    }

    /**
     * Checks if the current task associated with this context needs to be cancelled.
     */
    public isCancelled(): boolean {
        return this.cancellationChecker();
    }
}