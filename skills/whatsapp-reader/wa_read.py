import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERMES = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "whatsapp"
BRIDGE = "http://127.0.0.1:3000"


def load(path):
    seen = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        seen[m["id"]] = m
    return sorted(seen.values(), key=lambda m: m["ts"])


def phone_for(chat_id, session):
    f = session / f"lid-mapping-{chat_id.split('@')[0]}_reverse.json"
    if chat_id.endswith("@lid") and f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return chat_id.split("@")[0] if chat_id.endswith("@s.whatsapp.net") else ""


def group_name(chat_id):
    try:
        with urllib.request.urlopen(f"{BRIDGE}/chat/{chat_id}", timeout=3) as r:
            return json.load(r).get("name", "")
    except Exception:
        return ""


def chat_label(chat_id, msgs):
    if chat_id.endswith("@g.us"):
        return group_name(chat_id) or "group"
    names = [m["name"] for m in msgs if not m["fromMe"] and m["name"]]
    return names[-1] if names else ""


def chats(store, session):
    out = []
    for f in sorted(store.glob("*.jsonl")):
        msgs = load(f)
        if msgs:
            cid = msgs[-1]["chatId"]
            out.append((cid, phone_for(cid, session), chat_label(cid, msgs), len(msgs), msgs[-1]["ts"]))
    return out


def find_chat(query, store, session):
    q = query.lower().lstrip("+")
    hits = [c for c in chats(store, session) if q in c[0].lower() or (c[1] and q in c[1]) or q in c[2].lower()]
    return hits


def fmt(m):
    t = datetime.fromtimestamp(m["ts"]).strftime("%Y-%m-%d %H:%M")
    return f"{t} {m['name'] or m['sender'].split('@')[0]}: {m['text']}"


def main(argv=None):
    p = argparse.ArgumentParser(description="Read WhatsApp messages saved by the Hermes bridge.")
    p.add_argument("--store", type=Path, default=HERMES / "store")
    p.add_argument("--session", type=Path, default=HERMES / "session")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("chats")
    r = sub.add_parser("read")
    r.add_argument("chat", help="chat id, phone number, contact name or group name (substring)")
    r.add_argument("--last", type=int, default=30)
    r.add_argument("--hours", type=float)
    a = p.parse_args(argv)

    if a.cmd == "chats":
        rows = chats(a.store, a.session)
        if not rows:
            print("No saved chats. Add chats to WHATSAPP_READ_CHATS in the Hermes .env.")
        for cid, phone, label, n, ts in rows:
            print(f"{label or '?'} | {phone or '-'} | {cid} | {n} msgs | last {datetime.fromtimestamp(ts):%Y-%m-%d %H:%M}")
        return 0

    hits = find_chat(a.chat, a.store, a.session)
    if len(hits) != 1:
        print(f"{len(hits)} chats match {a.chat!r}." + "".join(f"\n  {h[2] or '?'} | {h[1] or '-'} | {h[0]}" for h in hits))
        return 1
    msgs = load(a.store / f"{hits[0][0]}.jsonl")
    if a.hours:
        cutoff = (datetime.now() - timedelta(hours=a.hours)).timestamp()
        msgs = [m for m in msgs if m["ts"] >= cutoff]
    print(f"{hits[0][2] or hits[0][0]} ({len(msgs[-a.last:])} of {len(msgs)} messages)")
    for m in msgs[-a.last:]:
        print(fmt(m))
    return 0


if __name__ == "__main__":
    sys.exit(main())
