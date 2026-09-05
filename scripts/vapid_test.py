#!/usr/bin/env python3
"""Data-free checks for VAPID public key normalization."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = r"""
import {
  isValidVapidPublicKey,
  normalizeVapidPublicKey,
  resolveVapidPublicKey,
  urlBase64ToUint8Array,
} from "./dashboard/lib/vapid.ts";

// web-push sample public key (URL-safe base64, 65-byte uncompressed point)
const SAMPLE =
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";

if (!isValidVapidPublicKey(SAMPLE)) throw new Error("sample key invalid");
const bytes = urlBase64ToUint8Array(SAMPLE);
if (bytes.length !== 65 || bytes[0] !== 0x04) throw new Error("sample decode");

const quoted = '"' + SAMPLE + '"';
if (normalizeVapidPublicKey(quoted) !== SAMPLE) throw new Error("quote strip");

const withWhitespace = "  " + SAMPLE + "  ";
if (!isValidVapidPublicKey(withWhitespace)) throw new Error("whitespace strip");

if (resolveVapidPublicKey("not-a-key", SAMPLE) !== SAMPLE) throw new Error("resolve fallback");
if (resolveVapidPublicKey("not-a-key", null) !== null) throw new Error("resolve null");

console.log("vapid_test: OK");
"""

proc = subprocess.run(["npx", "tsx", "-e", TS], cwd=ROOT, capture_output=True, text=True)
if proc.returncode != 0:
    print(proc.stdout)
    print(proc.stderr, file=sys.stderr)
    sys.exit(proc.returncode)
print(proc.stdout.strip())
