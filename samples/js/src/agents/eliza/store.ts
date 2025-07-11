import {
    ClientAgentSession,
    ClientAgentSessionStore,
    ClientAgentSessionUpdates
} from "@agentic-profile/auth";

export interface SessionContextStore {
    saveContext( sessionId: string, contextId: string, context: unknown ): Promise<void>;
    loadContext( sessionId: string, contextId: string ): Promise<unknown>;
}

export class InMemoryUnifiedStore implements ClientAgentSessionStore, SessionContextStore {
    private nextSessionId = 1;
    private clientSessions = new Map<number,ClientAgentSession>();
    private contextStore = new Map<string, unknown>();

    // ClientAgentSessionStore methods
    async createClientAgentSession( challenge: string ) {
        const id = this.nextSessionId++;
        this.clientSessions.set( id, { id, challenge, created: new Date() } as ClientAgentSession );
        return id;
    }

    async fetchClientAgentSession( id:number ) {
        return this.clientSessions.get( id );  
    }

    async updateClientAgentSession( id:number, updates:ClientAgentSessionUpdates ) {
        const session = this.clientSessions.get( id );
        if( !session )
            throw new Error("Failed to find client session by id: " + id );
        else
            this.clientSessions.set( id, { ...session, ...updates } );
    }

    // SessionContextStore methods
    async saveContext( sessionId: string, contextId: string, context: unknown ): Promise<void> {
        this.contextStore.set( `${sessionId}:${contextId}`, context );
    }

    async loadContext( sessionId: string, contextId: string ): Promise<unknown> {
        return this.contextStore.get( `${sessionId}:${contextId}` );
    }
}