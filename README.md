# hermes

**Version 0.1.0**

Changes and tools on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) that turn its WhatsApp gateway into a personal assistant you control from one private group:

- The agent runs on your own WhatsApp number and only acts on messages **you** type in a home group (a group with just you in it).
- It can **read** chats you choose, saved locally on your machine.
- It can **draft** replies to chats you choose, and a draft is sent only when you approve it by typing `send CODE` in the home group.
- A local **control page** lets you pick which chats it may read and draft for.

Built and tested against Hermes Agent v0.23.0 (commit `90d6b98`) on Windows 11.

## How it works

Everything that differs from a stock Hermes install lives in this repo:

| Path | What it is |
|---|---|
| `patches/hermes-agent.patch` | Changes to the Hermes WhatsApp bridge (`scripts/whatsapp-bridge/bridge.js`) and adapter (`plugins/platforms/whatsapp/adapter.py`), as a git patch against upstream |
| `skills/whatsapp-reader/` | A Hermes skill: `wa_read.py` reads saved chats, `wa_draft.py` creates drafts |
| `hermes_sync.py` | Applies the patch and skill to your Hermes install, or exports local edits back here |
| `control.py` | Local control page on http://127.0.0.1:8765 |
| `env.example`, `config.example.yaml` | The settings these features need |

What the patch adds to the bridge:

- **Owner-only intake.** Messages you did not type are dropped (`WHATSAPP_OWNER_ONLY`).
- **Replayed history is ignored.** WhatsApp replays recent messages on every reconnect; anything older than the bridge's start is skipped, so old chat lines never become commands.
- **Home group.** One group becomes the agent's chat (`WHATSAPP_HOME_GROUP`); your "You" chat and every other chat are ignored.
- **Message store.** Messages from chats in `WHATSAPP_READ_CHATS` are appended to one JSONL file per chat under `%LOCALAPPDATA%\hermes\whatsapp\store\`. Media is recorded as `[image]`, `[audio]` and so on; its content is not saved.
- **Approval-gated drafts.** `POST /draft` posts a coded draft to the home group. The bridge sends it to the target chat only when you type `send CODE` within 30 minutes. Drafts are only allowed for chats in `WHATSAPP_SEND_CHATS`.
- **Send lock.** Every send and edit endpoint returns 403 for any chat other than the home group, and outgoing text that looks like `send CODE` is refused, so the agent cannot send elsewhere or approve its own draft.
- **`GET /groups`** lists your groups for the control page.

## Setup

Requirements: Hermes Agent installed with its WhatsApp gateway paired (`hermes whatsapp`), Python 3.11+, and git.

1. Clone this repo.
2. Apply the patch and install the skill:
   ```
   python hermes_sync.py apply
   ```
   It reports any settings from `env.example` that are missing from your Hermes `.env`.
3. Add the settings from `env.example` to `%LOCALAPPDATA%\hermes\.env`:
   - `WHATSAPP_ALLOWED_USERS`: your number, country code, digits only.
   - `WHATSAPP_HOME_GROUP` and `WHATSAPP_GROUP_ALLOWED_USERS`: the ID of your home group (`<digits>@g.us`). The control page lists group IDs once the bridge is running.
4. Merge what you need from `config.example.yaml` into `%LOCALAPPDATA%\hermes\config.yaml` (model order, local terminal, quiet progress).
5. Start the gateway in your own terminal:
   ```
   hermes gateway
   ```
   The first WhatsApp connect usually logs `whatsapp connect timed out after 30s` and succeeds on the retry about 30 seconds later.

## Usage

**Control page**

```
python control.py
```

Open http://127.0.0.1:8765. Each chat has a **Read** and a **Draft** toggle. Changes are written to `.env`; press **Restart bridge** to apply them. The page only listens on 127.0.0.1.

**In the home group**

- `what's been happening in <group name> today?` reads the saved chat.
- `draft a reply in <group name> saying I'll be late` makes a draft and posts its code.
- `send CODE` (typed by you) sends that draft. Ignore a draft and it expires after 30 minutes.
- After adding or changing a skill, type `/new` so the next conversation loads it.

## After a Hermes update

`hermes update` stashes local changes to Hermes files, which removes the patch. Re-apply it:

```
python hermes_sync.py status
python hermes_sync.py apply
```

If Hermes changed the same files, `apply` reports a conflict instead of breaking anything.

If you edit the bridge or the skill inside your Hermes install, copy the edits back into this repo:

```
python hermes_sync.py export
```

## Restarting the bridge

Restarting the gateway does not always restart the bridge: a new gateway can attach to the bridge process that is already running and keep its old code and settings. Check `http://127.0.0.1:3000/health`; if `uptime` is older than your restart, use the control page's **Restart bridge** button or kill the `bridge.js` node process. The gateway starts a fresh one.

## Tests

```
uvx pytest
```

## Limits

- Tested only on Windows 11 with Hermes v0.23.0.
- Only messages that arrive after a chat is added to `WHATSAPP_READ_CHATS` are saved, plus whatever WhatsApp replays on reconnect.
- Saved messages are plain text on disk. Choose read chats with that in mind.
- The model order on the control page is display-only.

## Changelog

### 0.1.0 (2026-11-07)

- Owner-only intake and replayed-history filter for the WhatsApp bridge.
- Home group support.
- Message store and `whatsapp-reader` skill.
- Approval-gated drafts and send lock.
- Group listing endpoint and local control page.
- `hermes_sync.py` to apply, check and export the patch.
