import json
import tempfile
from pathlib import Path

import wa_read


def test_read_dedupes_sorts_and_finds_by_name_and_phone(capsys):
    with tempfile.TemporaryDirectory() as d:
        store, session = Path(d, "store"), Path(d, "session")
        store.mkdir(); session.mkdir()
        cid = "100000000000001@lid"
        (session / "lid-mapping-100000000000001_reverse.json").write_text('"910000000001"')
        rows = [
            {"id": "b", "ts": 200, "chatId": cid, "sender": cid, "fromMe": False, "name": "Rahul", "text": "second"},
            {"id": "a", "ts": 100, "chatId": cid, "sender": "me", "fromMe": True, "name": "me", "text": "first"},
            {"id": "b", "ts": 200, "chatId": cid, "sender": cid, "fromMe": False, "name": "Rahul", "text": "second"},
        ]
        (store / f"{cid}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")

        assert wa_read.main(["--store", str(store), "--session", str(session), "read", "rahul"]) == 0
        out = capsys.readouterr().out.splitlines()
        assert out[0] == "Rahul (2 of 2 messages)"
        assert out[1].endswith("me: first") and out[2].endswith("Rahul: second")

        assert wa_read.main(["--store", str(store), "--session", str(session), "read", "+910000000001", "--last", "1"]) == 0
        assert capsys.readouterr().out.splitlines()[1].endswith("Rahul: second")

        assert wa_read.main(["--store", str(store), "--session", str(session), "read", "nobody"]) == 1
