import {
  AgentCard,
  AgentExtension,
  Artifact,
  Message,
  Role,
  Task,
  TaskState,
} from '@a2a-js/sdk';
import {
  AgentExecutionEvent,
  RequestContext,
} from '@a2a-js/sdk/server';

const CORE_PATH = 'github.com/a2aproject/a2a-samples/extensions/timestamp/v1';
export const URI = `https://${CORE_PATH}`;
export const TIMESTAMP_FIELD = `${CORE_PATH}/timestamp`;

export function findExtensionByUri(card: AgentCard, uri: string): AgentExtension | undefined {
  return card.capabilities?.extensions?.find((ext) => ext.uri === uri);
}

export class TimestampExtension {
  private readonly nowFn: () => number;
  private readonly agentExtension: AgentExtension;

  constructor(nowFn?: () => number) {
    this.nowFn = nowFn || (() => Date.now() / 1000);
    this.agentExtension = {
      uri: URI,
      description: 'Adds timestamps to messages and artifacts.',
      required: false,
      params: undefined,
    };
  }

  addToCard(card: AgentCard): AgentCard {
    if (!card.capabilities) {
      card.capabilities = {
        streaming: false,
        extendedAgentCard: false,
        extensions: [],
        pushNotifications: false,
      };
    }
    if (!card.capabilities.extensions) {
      card.capabilities.extensions = [];
    }
    card.capabilities.extensions.push(this.agentExtension);
    return card;
  }

  isSupported(card?: AgentCard): boolean {
    if (card) {
      return findExtensionByUri(card, URI) !== undefined;
    }
    return false;
  }

  isRequested(context: RequestContext): boolean {
    return context.context.requestedExtensions?.includes(URI) || false;
  }

  applyTimestamp(o: Message | Artifact): void {
    if (this.hasTimestamp(o)) {
      return;
    }
    const now = this.nowFn();
    const date = new Date(now * 1000);
    if (!o.metadata) {
      o.metadata = {};
    }
    o.metadata[TIMESTAMP_FIELD] = date.toISOString();
  }

  timestampEvent(event: AgentExecutionEvent): void {
    for (const o of this.getMessagesInEvent(event)) {
      this.applyTimestamp(o);
    }
  }

  hasTimestamp(o: Message | Artifact): boolean {
    return o.metadata !== undefined && TIMESTAMP_FIELD in o.metadata;
  }

  private getMessagesInEvent(event: AgentExecutionEvent): (Message | Artifact)[] {
    switch (event.kind) {
      case 'statusUpdate':
        if (event.data.status?.message) {
          return [event.data.status.message];
        }
        return [];
      case 'artifactUpdate':
        if (event.data.artifact) {
          return [event.data.artifact];
        }
        return [];
      case 'message':
        return [event.data];
      case 'task':
        return this.getArtifactsAndMessagesInTask(event.data);
      default:
        return [];
    }
  }

  private getArtifactsAndMessagesInTask(t: Task): (Message | Artifact)[] {
    const results: (Message | Artifact)[] = [];
    if (t.artifacts) {
      results.push(...t.artifacts);
    }
    if (t.history) {
      results.push(...t.history.filter((m) => m.role === Role.ROLE_AGENT));
    }
    if (t.status?.message) {
      results.push(t.status.message);
    }
    return results;
  }
}
