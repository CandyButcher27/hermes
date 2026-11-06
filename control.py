import json
import os
import re
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERMES = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
ENV = HERMES / ".env"
CONFIG = HERMES / "config.yaml"
WA = HERMES / "whatsapp"
BRIDGE = "http://127.0.0.1:3000"
PORT = 8765
LISTS = {"read": "WHATSAPP_READ_CHATS", "send": "WHATSAPP_SEND_CHATS"}


def env_get(text, key):
    m = re.search(rf"^{key}=(.*)$", text, re.M)
    return [v.strip() for v in m.group(1).split(",") if v.strip()] if m else []


def env_set(text, key, values):
    line = f"{key}={','.join(values)}"
    if re.search(rf"^{key}=", text, re.M):
        return re.sub(rf"^{key}=.*$", line, text, count=1, flags=re.M)
    return text.rstrip("\n") + "\n" + line + "\n"


def toggle(text, key, chat_id, on):
    values = [v for v in env_get(text, key) if v != chat_id]
    return env_set(text, key, values + [chat_id] if on else values)


def bridge(path):
    try:
        with urllib.request.urlopen(BRIDGE + path, timeout=10) as r:
            return json.load(r)
    except Exception:
        return None


def dm_chats():
    found = {}
    for f in (WA / "store").glob("*.jsonl"):
        cid = f.stem
        if cid.endswith("@g.us"):
            continue
        names = [json.loads(l).get("name") for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
        found[cid] = next((n for n in reversed(names) if n and n != "me"), "")
    log = WA / "bridge.log"
    if log.exists():
        for cid in set(re.findall(r'"chatId":"([0-9]{6,}@(?:lid|s\.whatsapp\.net))"',log.read_text(encoding="utf-8", errors="replace"))):
            found.setdefault(cid, "")
    out = []
    for cid, name in found.items():
        num = cid.split("@")[0]
        rev = WA / "session" / f"lid-mapping-{num}_reverse.json"
        phone = json.loads(rev.read_text()) if cid.endswith("@lid") and rev.exists() else (num if cid.endswith("s.whatsapp.net") else "")
        out.append({"id": cid, "name": name or phone or num, "kind": "dm", "detail": phone})
    return out


def models():
    text = CONFIG.read_text(encoding="utf-8")
    head = re.search(r"^model:\n  default: (\S+)\n  provider: (\S+)", text, re.M)
    chain = re.findall(r"^  - provider: (\S+)\n    model: (\S+)", text, re.M)
    return ([f"{head.group(2)} / {head.group(1)}"] if head else []) + [f"{p} / {m}" for p, m in chain]


def state():
    text = ENV.read_text(encoding="utf-8")
    home = (env_get(text, "WHATSAPP_HOME_GROUP") or [""])[0]
    lists = {k: set(env_get(text, v)) for k, v in LISTS.items()}
    groups = bridge("/groups") or []
    chats = [{"id": g["id"], "name": g["name"], "kind": "group", "detail": f"{g['size']} members"} for g in groups if g["id"] != home]
    chats += dm_chats()
    for c in chats:
        c.update({k: c["id"] in lists[k] for k in LISTS})
    chats.sort(key=lambda c: (not (c["read"] or c["send"]), c["kind"], c["name"].lower()))
    return {
        "health": bridge("/health"),
        "home": next((g["name"] for g in groups if g["id"] == home), home),
        "models": models(),
        "chats": chats,
        "groupsLoaded": bool(groups),
    }


def restart_bridge():
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'bridge\\.js' } | % { Stop-Process -Id $_.ProcessId -Force }"],
        check=False, capture_output=True,
    )


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            return self.reply(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/state":
            return self.reply(200, state())
        self.reply(404, {"error": "not found"})

    def do_POST(self):
        if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"):
            return self.reply(403, {"error": "bad origin"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/chat":
            if body.get("list") not in LISTS or not re.fullmatch(r"[0-9]+@(g\.us|lid|s\.whatsapp\.net)", str(body.get("id"))):
                return self.reply(400, {"error": "bad request"})
            ENV.write_text(toggle(ENV.read_text(encoding="utf-8"), LISTS[body["list"]], body["id"], bool(body.get("on"))), encoding="utf-8")
            return self.reply(200, {"ok": True})
        if self.path == "/api/restart-bridge":
            restart_bridge()
            return self.reply(200, {"ok": True})
        self.reply(404, {"error": "not found"})

    def log_message(self, *args):
        pass


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hermes Control</title>
<style>
:root{--bg:#f6f5f1;--fg:#1d1d1b;--muted:#6b6a65;--line:#dedcd4;--card:#fff;--accent:#2f6d4f;--warn:#a2462b}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--muted:#9a988f;--line:#2e2d29;--card:#1f1e1b;--accent:#6fbf94;--warn:#e08b6d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:880px;margin:0 auto;padding:24px 16px 64px}h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--muted);margin:0 0 20px}.row{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;flex:1 1 240px}
.card b{display:block;font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.ok{color:var(--accent)}.bad{color:var(--warn)}
input[type=search]{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font:inherit;margin-bottom:8px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line)}th{font-size:12px;color:var(--muted);font-weight:600}
td.c,th.c{text-align:center;width:70px}.k{font-size:12px;color:var(--muted)}tr:last-child td{border-bottom:0}
button{font:inherit;padding:8px 14px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.note{color:var(--muted);font-size:13px;margin:10px 0 0}#dirty{display:none;color:var(--warn);margin-left:8px}
</style></head><body><main>
<h1>Hermes Control</h1><p class="sub">Which WhatsApp chats Hermes may read, and which it may draft replies for. Drafts are only sent when you type <code>send CODE</code> in the home group.</p>
<div class="row">
<div class="card"><b>Bridge</b><span id="health">…</span></div>
<div class="card"><b>Home group</b><span id="home">…</span></div>
<div class="card"><b>Model order</b><span id="models">…</span></div>
</div>
<div class="row" style="align-items:center"><button class="primary" id="restart">Restart bridge</button><span id="dirty">Changes saved. Restart the bridge to apply them.</span></div>
<input type="search" id="q" placeholder="Filter chats by name or number">
<table><thead><tr><th>Chat</th><th class="c">Read</th><th class="c">Draft</th></tr></thead><tbody id="rows"></tbody></table>
<p class="note" id="note"></p>
</main><script>
let chats=[];
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(){
  const s=await (await fetch('/api/state')).json();
  const h=s.health;
  document.getElementById('health').innerHTML=h?`<span class="${h.status==='connected'?'ok':'bad'}">${esc(h.status)}</span> · up ${Math.round(h.uptime/60)} min`:'<span class="bad">not running</span>';
  document.getElementById('home').textContent=s.home||'not set';
  document.getElementById('models').innerHTML=s.models.map((m,i)=>`${i+1}. ${esc(m)}`).join('<br>');
  document.getElementById('note').textContent=s.groupsLoaded?'':'Group list unavailable: the bridge is down or not restarted since the /groups endpoint was added.';
  chats=s.chats;render();
}
function render(){
  const q=document.getElementById('q').value.toLowerCase();
  document.getElementById('rows').innerHTML=chats.filter(c=>!q||(c.name+' '+c.detail+' '+c.id).toLowerCase().includes(q)).map(c=>
    `<tr><td>${esc(c.name)}<div class="k">${c.kind==='group'?'Group':'Contact'} · ${esc(c.detail||c.id)}</div></td>`+
    ['read','send'].map(l=>`<td class="c"><input type="checkbox" data-id="${esc(c.id)}" data-list="${l}" ${c[l]?'checked':''}></td>`).join('')+'</tr>').join('');
}
document.getElementById('q').oninput=render;
document.getElementById('rows').onchange=async e=>{
  const t=e.target,c=chats.find(x=>x.id===t.dataset.id);
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:t.dataset.id,list:t.dataset.list,on:t.checked})});
  if(r.ok){c[t.dataset.list]=t.checked;document.getElementById('dirty').style.display='inline'}else{t.checked=!t.checked;alert('Save failed')}
};
document.getElementById('restart').onclick=async()=>{
  const b=document.getElementById('restart');b.disabled=true;b.textContent='Restarting…';
  await fetch('/api/restart-bridge',{method:'POST'});
  for(let i=0;i<45;i++){await new Promise(r=>setTimeout(r,2000));const h=(await (await fetch('/api/state')).json()).health;if(h&&h.status==='connected'&&h.uptime<120)break}
  b.disabled=false;b.textContent='Restart bridge';document.getElementById('dirty').style.display='none';load();
};
load();
</script></body></html>"""


if __name__ == "__main__":
    print(f"Hermes control page: http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
