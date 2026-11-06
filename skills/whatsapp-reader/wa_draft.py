import argparse
import json
import sys
import urllib.error
import urllib.request

BRIDGE = "http://127.0.0.1:3000"


def main(argv=None):
    p = argparse.ArgumentParser(description="Draft a WhatsApp message for the owner to approve.")
    p.add_argument("chat", help="group name, phone number or chat id from WHATSAPP_SEND_CHATS")
    p.add_argument("text")
    a = p.parse_args(argv)
    req = urllib.request.Request(
        f"{BRIDGE}/draft",
        data=json.dumps({"chat": a.chat, "text": a.text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        print(f"Draft refused: {e.read().decode(errors='replace')}")
        return 1
    print(f"Draft {d['code']} for {d['name']} posted to the Hermes Agent group. "
          f"Nothing is sent until the owner replies \"send {d['code']}\" (expires in {d['expiresInMinutes']} min).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
