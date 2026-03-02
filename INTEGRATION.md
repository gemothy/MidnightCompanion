# DEGA ↔ MidnightCompanion Integration

This document covers:
1. **What was changed** — every DEGA-facing integration point built into MidnightCompanion
2. **What's missing** — why Companion chat currently doesn't persist into the simulation
3. **The roadmap** — concrete steps to make chat truly impact agents over the long haul

---

## 1. What was built

### 1.1 Read-only data layer (Flask proxies)

MidnightCompanion avoids CORS by routing all DEGA API calls through Flask:

| Flask route | DEGA endpoint | What it returns |
|---|---|---|
| `GET /dega/agents` | `:8080/api/agents` | Full agent roster |
| `GET /dega/agents/:id` | `:8080/api/agents/:id` | Profile: personality, traits, backstory, tone |
| `GET /dega/agents/:id/metrics` | `:8080/api/agents/:id/metrics` then DB fallback | Success rate, action count, insight count |
| `GET /dega/character/:slug/:file` | `:8080/api/characters/:slug/assets/:file` | Sprite PNG for Phaser |

The metrics endpoint has a **PostgreSQL fallback** — if the REST endpoint fails, Flask queries the DB directly for transaction counts and success rates.

### 1.2 Real-time event stream (Socket.IO viewer)

The frontend connects to the DEGA game server at `:4000/io` as a **viewer** (`viewer:connect` event). It listens to:

| Game event | What triggers it | What Companion does |
|---|---|---|
| `game:chat` | Agent sends a chat message | Speech bubble + event log + appends to chat log |
| `game:walkingState` | Agent begins moving to a target | Status → "Heading to X…" + event pill |
| `game:waitingState` | Agent enters thinking/acting/idle | Status update |
| `game:arrivedAtTarget` | Agent reaches destination | Status + district + event pill |
| `game:mcpTransaction` | Agent calls a Midnight blockchain tool | Status + event pill with operation name |
| `game:dayCycleStage` | Day/night cycle changes | One-off bubble |
| `game:position` | Agent moves one tile | *(no-op — too noisy)* |

### 1.3 Bot presence (Socket.IO `/bot` namespace)

The Companion joins the game server's `/bot` namespace as `Companion`. This means:

- The game server logs the connection: `[/bot] Companion connected`
- When the user sends a chat, the message is relayed as: `Companion: Avelin Verdant, <message>`
- The game server broadcasts it to TCP-connected players and viewers
- **Crucially: AI agents do NOT receive this message** (see §2 below)

### 1.4 In-character chat (Gemini 2.0 Flash)

`POST /chat` provides the illusion of talking to the agent:

1. Fetches agent profile from DEGA (`personality_traits`, `conversation_style`, `backstory`, `tone`)
2. Fetches 6 most recent unique memories from DEGA memory API
3. Builds a system prompt that puts Gemini in character
4. Calls `gemini-2.0-flash` via the `GOOGLE_API_KEY` from env
5. Returns response shown as speech bubble + chat message

This is a **stateless simulation** — Gemini doesn't remember previous Companion chats. Each request is fresh.

### 1.5 Mobile & LAN access

- Flask binds to `0.0.0.0` — accessible on the local network
- Frontend uses `window.location.hostname` to auto-construct DEGA/WS URLs — no hardcoded `localhost`, works from any device on the same WiFi

---

## 2. Why Companion chat doesn't (yet) affect agents

### 2.1 The DEGA message routing gap

When the Companion sends a chat via `/bot`:

```
Companion (browser)
  → Socket.IO /bot namespace
  → Game server handleBotChat()
  → TCP broadcast to connected AI agents
  → Agent TCP adapter receives raw message
  → Emits internal `chat` event
  → ❌ No listener for external chat during idle state
  → Agent's cognitive loop (fires every ~45 min) doesn't include world chat
  → Agent never processes or responds
```

The game server's `handleBotChat` broadcasts to TCP players and `notifyViewers`, but the AI agents' idle loop has no handler for incoming world chat.

### 2.2 The cognitive loop architecture

Each DEGA agent runs a LangGraph cognitive loop that fires every ~2,335 seconds (~39 min). The loop:
1. Gathers context: current location, nearby agents, recent memories, trust scores
2. Decides action: move, talk to nearby agent, or call MCP blockchain tool
3. Executes and stores results as ChromaDB memories

World chat from external sources (like Companion) is **not part of this context**. Even if the message arrives at the agent adapter, the loop doesn't query for it.

### 2.3 Agent-to-agent chat IS consequential

When two DEGA agents chat with each other:
- The message is processed by both agents' cognitive loops
- Stored as ChromaDB memories (searchable in future decisions)
- Trust/relationship scores are updated
- Affects future agent behavior (who to approach, what to share)

This pipeline is working and battle-tested. The Companion needs to plug into it.

---

## 3. Roadmap: making Companion chat truly persistent

### Phase 1 — Persistent memory injection (minimal DEGA change)

**Goal:** Companion messages get stored as agent memories, influencing future decisions.

**What to build:**
- Add a `POST /api/agents/:id/memories` endpoint to the DEGA AI agent server (or use the existing ChromaDB client directly)
- After each Companion `/chat` call, also write the conversation turn as a memory:
  ```json
  {
    "content": "A visitor named [user] asked: 'What are you working on?' I replied: '...'",
    "type": "external_conversation",
    "importance": 0.6,
    "timestamp": "..."
  }
  ```
- The agent's next cognitive loop will retrieve this memory when it searches ChromaDB for relevant context

**Impact:** Agent will "remember" conversations with the Companion and reference them in future decisions, even without real-time awareness.

---

### Phase 2 — Real-time message injection (moderate DEGA change)

**Goal:** When a Companion message arrives, the target agent processes it within seconds rather than waiting for the next cognitive loop.

**Option A — Game server chat bridge:**
In `handleBotChat()` on the game server, instead of only broadcasting to TCP viewers, also emit a special `companion:message` event to the AI agent server via HTTP:
```js
// game server handleBotChat addition
await fetch(`http://ai-agents:8080/api/agents/${targetAgent}/inbox`, {
  method: 'POST',
  body: JSON.stringify({ from: 'Companion', message })
})
```

The AI agent server then interrupts (or queues for) the next loop iteration to include this message.

**Option B — Direct agent inbox via MCP:**
Use DEGA's existing MCP server (38 tools). Add a `send_message_to_agent` MCP tool that drops a message into the agent's context queue. Nyx already has `CALL_MCP_TOOL` — this would make the integration work through the full Nyx → MCP → DEGA chain.

---

### Phase 3 — Companion identity in the simulation (deep integration)

**Goal:** The Companion becomes a named entity in the simulation — agents know who they're talking to and can reference the relationship.

**What to build:**
- Register "Companion" as a pseudo-agent in the DEGA agent roster with a profile (name, role, trust baseline)
- Agent trust scores include `Companion` as a relationship
- Conversations are bidirectional: agent memories reference "spoke with Companion about X"
- The Companion's chat history is persisted (session or DB), so Gemini gets full conversation context rather than a fresh prompt each time

---

### Phase 4 — Closing the loop (full integration)

**Goal:** Agents can initiate contact with the Companion, not just respond.

- When an agent decides to "send message to external observer" as a cognitive action, it calls an MCP tool that POSTs to a Companion webhook
- The Companion receives the unsolicited message, shows it as a speech bubble, and optionally notifies the user (push notification, Discord DM via Nyx)
- Nyx integration: Nyx's Discord/Telegram channel becomes a relay — messages sent to Nyx get forwarded to the target agent via MCP, and agent responses come back through Nyx

---

## 4. Current state summary

| Feature | Status |
|---|---|
| View agent live (sprite, room, state) | ✅ Working |
| Real-time events (chat, walk, MCP tx) | ✅ Working |
| Agent stats (success, actions, insights) | ✅ Working |
| In-character Gemini chat response | ✅ Working (stateless) |
| Companion message visible in game world | ✅ Working (bot broadcast) |
| Agent processes Companion message | ❌ Not implemented |
| Companion chat stored as agent memory | ❌ Not implemented |
| Persistent Companion conversation history | ❌ Not implemented |
| Agents initiate contact with Companion | ❌ Not implemented |
| Nyx ↔ Companion ↔ DEGA relay | ❌ Not implemented |

---

## 5. Files changed

### `backend/app.py`
- Added DEGA proxy routes (`/dega/agents`, `/dega/agents/:id`, metrics, character assets)
- Added PostgreSQL metrics fallback
- Added `POST /chat` — Gemini 2.0 Flash in-character response with agent profile + memory context
- SSL certificate bypass for Gemini API (`ssl.CERT_NONE`)
- Flask binds to `0.0.0.0` for LAN access

### `frontend/index.html`
- Full rewrite of static status UI → live DEGA viewer
- Phaser 3 scene: dynamic agent sprite loading from DEGA character API
- Socket.IO viewer connection to `:4000/io` — game event handlers
- Socket.IO bot connection to `:4000/bot` — Companion presence + world chat relay
- Stats panel: REST poll every 30s
- Event log: real-time notification pills (chat, walk, MCP tx, day cycle)
- In-character chat UI: typing indicator, Gemini response, speech bubble
- Mobile layout: two-row top bar, centered controls, safe-area insets, dark chat panel
- LAN fix: DEGA/WS URLs derived from `window.location.hostname`
