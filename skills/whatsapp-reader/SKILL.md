---
name: whatsapp-reader
description: "Read the owner's saved WhatsApp chats (messages, who said what, recent activity) on request."
version: 0.1.0
author: CandyButcher27
license: MIT
platforms: [windows]
prerequisites:
  commands: [python]
metadata:
  hermes:
    tags: [whatsapp, messages, chats, read]
---

# WhatsApp reader

The WhatsApp bridge saves messages from the chats listed in `WHATSAPP_READ_CHATS` (Hermes `.env`).
Use this skill when the owner asks what someone said, to summarise a chat, or what is new in a chat.

## Commands

List saved chats (name | phone | chat id | count | last message time):

    python "{SKILL_DIR}/wa_read.py" chats

Read a chat. `<chat>` is a contact name, group name, phone number or chat id; a substring is enough:

    python "{SKILL_DIR}/wa_read.py" read "<chat>" --last 50
    python "{SKILL_DIR}/wa_read.py" read "<chat>" --hours 24

If more than one chat matches, the script lists them; pick one or ask the owner.

## Rules

- Read only. Never send a message to any chat other than the one the owner is talking to you in.
- Only chats in `WHATSAPP_READ_CHATS` are saved, and only from when they were added. Say so if a chat is missing or history is short.
- Media shows as `[image]`, `[audio]` and so on; its content is not saved.
- Quote or summarise only what the owner asked about.
