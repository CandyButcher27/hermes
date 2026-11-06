import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HERMES = Path(os.environ.get("HERMES_HOME") or Path(os.environ.get("LOCALAPPDATA", "")) / "hermes")
AGENT = HERMES / "hermes-agent"
PATCH = ROOT / "patches" / "hermes-agent.patch"
FILES = ["scripts/whatsapp-bridge/bridge.js", "plugins/platforms/whatsapp/adapter.py"]
SKILL_SRC = ROOT / "skills" / "whatsapp-reader"
SKILL_DST = HERMES / "skills" / "social-media" / "whatsapp-reader"
TOKEN = "{SKILL_DIR}"


def git(*args, check=True):
    return subprocess.run(["git", "-C", str(AGENT), *args], capture_output=True, text=True, check=check)


def to_lf():
    for f in FILES:
        p = AGENT / f
        data = p.read_bytes()
        if b"\r\n" in data:
            p.write_bytes(data.replace(b"\r\n", b"\n"))


def patch_state():
    if git("apply", "--check", "--reverse", str(PATCH), check=False).returncode == 0:
        return "applied"
    if git("apply", "--check", str(PATCH), check=False).returncode == 0:
        return "clean"
    return "conflict"


def env_keys(text):
    return set(re.findall(r"^([A-Z_]+)=", text, re.M))


def apply():
    to_lf()
    state = patch_state()
    if state == "conflict":
        print("Patch does not apply: Hermes changed these files (an update?).")
        print(git("diff", "--stat", "--", *FILES).stdout or "Files match upstream; the patch itself conflicts with this Hermes version.")
        return 1
    if state == "clean":
        git("apply", str(PATCH))
    print("Hermes patch:", "already applied" if state == "applied" else "applied")
    SKILL_DST.mkdir(parents=True, exist_ok=True)
    for f in SKILL_SRC.glob("*.py"):
        shutil.copy2(f, SKILL_DST / f.name)
    skill = (SKILL_SRC / "SKILL.md").read_text(encoding="utf-8").replace(TOKEN, SKILL_DST.as_posix())
    (SKILL_DST / "SKILL.md").write_text(skill, encoding="utf-8")
    print("Skill installed:", SKILL_DST)
    env = HERMES / ".env"
    missing = env_keys((ROOT / "env.example").read_text(encoding="utf-8")) - env_keys(env.read_text(encoding="utf-8") if env.exists() else "")
    if missing:
        print("Missing in", env, ":", ", ".join(sorted(missing)))
    print("Restart the WhatsApp bridge to load bridge changes (control page button, or kill the bridge.js node process).")
    return 0


def export():
    to_lf()
    PATCH.parent.mkdir(exist_ok=True)
    PATCH.write_text(git("diff", "--", *FILES).stdout, encoding="utf-8", newline="\n")
    for f in SKILL_DST.glob("*.py"):
        shutil.copy2(f, SKILL_SRC / f.name)
    skill = (SKILL_DST / "SKILL.md").read_text(encoding="utf-8").replace(SKILL_DST.as_posix(), TOKEN)
    (SKILL_SRC / "SKILL.md").write_text(skill, encoding="utf-8", newline="\n")
    print("Exported patch and skill from", HERMES)
    return 0


def main():
    p = argparse.ArgumentParser(description="Sync this repo's Hermes changes with the local Hermes install.")
    p.add_argument("command", choices=["apply", "export", "status"])
    a = p.parse_args()
    if a.command == "status":
        to_lf()
        print("Hermes patch:", patch_state())
        return 0
    return apply() if a.command == "apply" else export()


if __name__ == "__main__":
    sys.exit(main())
