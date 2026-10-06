"""Check Git's index and history without displaying secret bytes."""

import re
import subprocess
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    tracked = git("ls-files", "-z").decode().split("\0")
    forbidden = [
        p
        for p in tracked
        if (Path(p).name.startswith(".env") and Path(p).name != ".env.example")
        or Path(p).name == "typesafe.txt"
    ]
    if forbidden:
        raise SystemExit("FAIL: private configuration is tracked")
    secrets = []
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.endswith("KEY") and len(value.strip()) >= 16:
                secrets.append(value.strip().strip("\"'").encode())
        subprocess.run(["git", "check-ignore", "-q", ".env"], check=True)
    ids = set()
    for line in git("rev-list", "--objects", "--all").splitlines():
        ids.add(line.split()[0].decode())
    for line in git("ls-files", "--stage").splitlines():
        ids.add(line.split()[1].decode())
    for oid in ids:
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        data = git("cat-file", "blob", oid)
        if any(secret in data for secret in secrets):
            raise SystemExit("FAIL: a configured secret occurs in Git content")
        if re.search(rb"(?:sk-ollm-|ts_live_)[A-Za-z0-9_-]{24,}", data):
            raise SystemExit("FAIL: possible credential in Git content")
    print("PASS: private files untracked; configured keys absent from index and history")


if __name__ == "__main__":
    main()
