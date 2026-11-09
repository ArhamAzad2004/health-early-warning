"""Write backend/requirements-lock.txt: every runtime package pinned with all its PyPI file hashes.

Usage (from the repo root, after changing backend/requirements.txt):
  backend/.venv/Scripts/python -m pip install --dry-run --ignore-installed --report report.json       --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64       --python-version 3.13 --implementation cp --only-binary=:all: --target tmp -r backend/requirements.txt
  python scripts/lock_requirements.py report.json backend/requirements-lock.txt
"""
import json, os, sys, urllib.request
report = json.load(open(sys.argv[1], encoding="utf8"))
pins = {i["metadata"]["name"]: i["metadata"]["version"] for i in report["install"]}
uv = json.load(urllib.request.urlopen("https://pypi.org/pypi/uvloop/json"))
pins["uvloop"] = uv["info"]["version"]  # Linux-only dependency of uvicorn[standard]; a Windows resolve skips it
lines = ["# Exact runtime packages for the Docker image (Linux), installed with --require-hashes.",
         "# Regenerate with scripts/lock_requirements.py when requirements.txt changes (see its docstring);",
         "# a backend test fails if this file drifts, and the CI Docker build fails if anything is missing.", ""]
for name in sorted(pins, key=str.lower):
    files = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{pins[name]}/json", timeout=60))["urls"]
    extra = "; sys_platform != 'win32'" if name == "uvloop" else ""
    lines.append(f"{name.lower()}=={pins[name]}{extra} \\")
    lines += [f"    --hash=sha256:{f['digests']['sha256']} \\" for f in files]
    lines[-1] = lines[-1].rstrip(" \\")
open(sys.argv[2], "w", newline="\n").write("\n".join(lines) + "\n")
print(len(pins), "packages; uvloop", pins["uvloop"])
