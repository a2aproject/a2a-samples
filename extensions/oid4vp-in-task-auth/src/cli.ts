#!/usr/bin/env node

import readline from 'node:readline'

import { MessageSendParams, Message, Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent, Part } from '@a2a-js/sdk'
import { A2AClient } from '@a2a-js/sdk/client'
import * as dotenv from 'dotenv'
import { createCredoAgent, CredoAgentWithOpenId4Vc } from './credo-helpers'
import { provisionVouchers } from './vouchers'
import { IN_TASK_OID4VP_EXTENSION_URI, InTaskOpenId4VpMessageMetadata } from './extension'
import { presentVoucher, PresentationOutcome, VoucherOption } from './holder-wallet'
import { uuid } from './a2a-helpers'

dotenv.config()

// ANSI colors
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
}

function colorize(color: keyof typeof colors, text: string): string {
  return `${colors[color]}${text}${colors.reset}`
}

const serverUrl = process.argv[2] || process.env.ASSISTANT_AGENT_URL || 'http://localhost:10004'
const client = new A2AClient(serverUrl)

let agentName = 'Agent'
let currentTaskId: string | undefined
let currentContextId: string | undefined

const rl = readline.createInterface({ input: process.stdin, output: process.stdout })

function question(prompt: string): Promise<string> {
  return new Promise((resolve) => rl.question(prompt, resolve))
}

function printMessageContent(message: Message) {
  message.parts.forEach((part: Part, index: number) => {
    const prefix = colorize('red', `  Part ${index + 1}:`)
    if (part.kind === 'text') {
      console.log(`${prefix} ${colorize('green', '📝 Text:')} ${part.text}`)
    } else if (part.kind === 'data') {
      console.log(`${prefix} ${colorize('yellow', '📊 Data:')}`, JSON.stringify(part.data))
    } else if (part.kind === 'file') {
      console.log(`${prefix} ${colorize('blue', '📄 File')}`)
    }
  })
}

function printAgentEvent(event: TaskStatusUpdateEvent | TaskArtifactUpdateEvent) {
  const ts = new Date().toLocaleTimeString()
  const prefix = colorize('magenta', `\n${agentName} [${ts}]:`)
  if (event.kind === 'status-update') {
    const state = event.status.state
    const emoji =
      { working: '⏳', 'input-required': '🤔', 'auth-required': '🔐', completed: '✅', canceled: '⏹️', failed: '❌' }[
        state as string
      ] ?? 'ℹ️'
    console.log(
      `${prefix} ${emoji} Status: ${colorize('cyan', state)} ${event.final ? colorize('bright', '[FINAL]') : ''}`
    )
    if (event.status.message) printMessageContent(event.status.message)
  } else if (event.kind === 'artifact-update') {
    console.log(`${prefix} 📄 Artifact: ${event.artifact.name || '(unnamed)'}`)
    printMessageContent({
      messageId: uuid(),
      kind: 'message',
      role: 'agent',
      parts: event.artifact.parts,
      taskId: event.taskId,
      contextId: event.contextId,
    })
  }
}

async function handleAuthRequest(
  credoAgent: CredoAgentWithOpenId4Vc,
  requestUri: string
): Promise<PresentationOutcome['status']> {
  const outcome = await presentVoucher(credoAgent, requestUri, {
    choose: async (options: VoucherOption[], purpose) => {
      console.log(
        colorize(
          'green',
          `\n🔐 The agent requested a verifiable credential${purpose ? ` (purpose: "${purpose}")` : ''}.`
        )
      )
      // Stable, readable order (the wallet's underlying match order is not guaranteed).
      const sorted = [...options].sort((a, b) =>
        String(a.claims.issuer_brand ?? a.claims.iss).localeCompare(String(b.claims.issuer_brand ?? b.claims.iss))
      )
      console.log(colorize('dim', `Your wallet holds ${sorted.length} matching credential(s):`))
      sorted.forEach((o, i) => {
        const c = o.claims
        console.log(
          `  ${colorize('bright', `[${i + 1}]`)} ${c.issuer_brand ?? c.iss} — ${c.percent_off}% off, expires ${c.expires_at}`
        )
      })
      const answer = (
        await question(colorize('cyan', `Choose a voucher to present (1-${sorted.length}), or 'n' to decline: `))
      ).trim()
      const choice = Number(answer)
      if (!Number.isInteger(choice) || choice < 1 || choice > sorted.length) return null
      return sorted[choice - 1]
    },
    confirm: async (requestedClaims) => {
      console.log(colorize('yellow', `\nPresenting will disclose ONLY: ${JSON.stringify(requestedClaims)}`))
      console.log(colorize('dim', `(Your identity, voucher id and issuing brand stay private.)`))
      const confirm = (await question(colorize('cyan', 'Confirm sharing? (yes/no): '))).trim().toLowerCase()
      return confirm === 'yes' || confirm === 'y'
    },
  })

  switch (outcome.status) {
    case 'sent':
      console.log(colorize('green', '✓ Presentation sent to the verifier.'))
      break
    case 'unsatisfiable':
      console.log(colorize('red', 'Your wallet has no credential that satisfies this request.'))
      break
    case 'declined':
      console.log(colorize('red', 'Authorization cancelled — unable to proceed with the task.'))
      break
    case 'failed':
      console.log(colorize('red', 'Failed to submit the presentation.'), outcome.detail)
      break
  }
  return outcome.status
}

async function createAndProvisionWallet(): Promise<CredoAgentWithOpenId4Vc> {
  // Holder-only Credo agent: it makes outbound OID4VP calls to the merchant's verifier and serves
  // no endpoints of its own, so it needs no express app or port.
  const credoAgent = createCredoAgent('a2a-client')
  await credoAgent.initialize()

  const vouchers = await provisionVouchers(credoAgent)

  console.log(colorize('green', `\n👛 Wallet provisioned with ${vouchers.length} discount voucher(s):`))
  for (const v of vouchers) {
    console.log(colorize('dim', `   • ${v.brand}: ${v.percentOff}% off (expires ${v.expiresAt})`))
  }

  return credoAgent
}

async function sendMessage(credoAgent: CredoAgentWithOpenId4Vc, text: string): Promise<void> {
  const message: Message = {
    messageId: uuid(),
    kind: 'message',
    role: 'user',
    parts: [{ kind: 'text', text }],
  }
  if (currentTaskId) message.taskId = currentTaskId
  if (currentContextId) message.contextId = currentContextId

  const params: MessageSendParams = { message }

  console.log(colorize('red', 'Sending message...'))
  const stream = client.sendMessageStream(params)

  for await (const event of stream) {
    if (event.kind === 'status-update') {
      const statusEvent = event as TaskStatusUpdateEvent
      printAgentEvent(statusEvent)

      if (statusEvent.status.state === 'auth-required') {
        const metadata = statusEvent.status.message?.metadata?.[IN_TASK_OID4VP_EXTENSION_URI] as
          | InTaskOpenId4VpMessageMetadata
          | undefined
        if (!metadata?.authorizationRequest) {
          console.log(colorize('yellow', "Received 'auth-required' without OID4VP metadata. Skipping."))
          continue
        }
        const outcome = await handleAuthRequest(credoAgent, metadata.authorizationRequest.request_uri)
        if (outcome !== 'sent') {
          // We won't present a credential. The merchant cannot be told out-of-band that we declined,
          // so it will move on only after its own auth timeout. Don't make the user wait for that:
          // abandon this turn and reset to a clean task + context so the next message starts fresh.
          currentTaskId = undefined
          currentContextId = undefined
          console.log(colorize('dim', '--- Authorization not completed; returning to the prompt. ---'))
          return
        }
      }

      if (statusEvent.status.state !== 'input-required' && statusEvent.final) {
        currentTaskId = undefined
      }
    } else if (event.kind === 'task') {
      const task = event as Task
      currentTaskId = task.id
      currentContextId = task.contextId
    } else if (event.kind === 'message') {
      const message = event as Message
      if (message.taskId) currentTaskId = message.taskId
      if (message.contextId) currentContextId = message.contextId
      printMessageContent(message)
    }
  }
  console.log(colorize('dim', `--- End of response stream ---`))
}

async function main() {
  console.log(colorize('bright', 'A2A Terminal Client (OID4VP In-Task Auth demo)'))
  console.log(colorize('dim', `Connecting to: ${serverUrl}`))

  const credoAgent = await createAndProvisionWallet()

  try {
    const card = await client.getAgentCard()
    agentName = card.name || 'Agent'
    console.log(colorize('green', `✓ Connected to "${agentName}".`))
  } catch {
    console.log(colorize('yellow', `⚠️ Could not fetch agent card from ${serverUrl} (is the agent running?).`))
  }

  console.log(colorize('green', `Type a message. Use '/new' to reset the session, '/exit' to quit.`))

  for (;;) {
    const input = (await question(colorize('cyan', `\n${agentName} > You: `))).trim()
    if (!input) continue
    if (input.toLowerCase() === '/exit') break
    if (input.toLowerCase() === '/new') {
      currentTaskId = undefined
      currentContextId = undefined
      console.log(colorize('bright', '✨ New session — task and context cleared.'))
      continue
    }
    try {
      await sendMessage(credoAgent, input)
    } catch (error: any) {
      console.error(colorize('red', `Error: ${error?.message ?? error}`))
    }
  }

  rl.close()
  await credoAgent.shutdown()
  console.log(colorize('yellow', 'Goodbye!'))
  process.exit(0)
}

main().catch((err) => {
  console.error(colorize('red', 'Unhandled error in main:'), err)
  process.exit(1)
})
