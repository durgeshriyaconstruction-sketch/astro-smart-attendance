#!/usr/bin/env python3
"""Regenerate firmware/astro_attendance/astro_certs.h from the system CA bundle.

Supabase's TLS edge chains to Google Trust Services or Let's Encrypt depending on
when the project certificate was renewed, so all likely roots are embedded.

The generated header holds ONE string literal (ASTRO_CA_BUNDLE) built by C++
adjacent-literal concatenation -- concatenating char *arrays* is not valid C++,
which is exactly the bug this script exists to prevent.

Usage:  python3 tools/make_certs_header.py [path/to/ca-bundle.pem]
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

WANTED = ["GTS Root R1", "ISRG Root X1", "ISRG Root X2"]
DEFAULT_BUNDLE = "/etc/ssl/certs/ca-certificates.crt"
OUT = Path(__file__).resolve().parent.parent / "firmware/astro_attendance/astro_certs.h"

HEADER = '''// ============================================================================
//  astro_certs.h  --  root CAs for <project-ref>.supabase.co
//
//  GENERATED FILE - do not edit by hand.
//  Regenerate with:  python3 tools/make_certs_header.py
//
//  Supabase's edge terminates TLS with Google Trust Services (GTS Root R1) or
//  Let's Encrypt (ISRG Root X1 / X2) depending on when the project certificate
//  was renewed. All three roots are embedded so a renewal never bricks the
//  terminal.
//
//  These are public root certificates (present in every browser and OS trust
//  store), not secrets.
// ============================================================================
#pragma once

#ifndef PROGMEM
#define PROGMEM
#endif

// Concatenated PEM bundle. mbedTLS parses every certificate in one buffer, so a
// single call to WiFiClientSecure::setCACert() trusts all of them.
static const char ASTRO_CA_BUNDLE[] PROGMEM =
{body};

static const int ASTRO_CA_BUNDLE_LEN = sizeof(ASTRO_CA_BUNDLE) - 1;
'''


def subject(pem: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as fh:
        fh.write(pem + "\n")
        name = fh.name
    try:
        out = subprocess.run(
            ["openssl", "x509", "-in", name, "-noout", "-subject"],
            capture_output=True, text=True, check=True,
        ).stdout
    finally:
        Path(name).unlink(missing_ok=True)
    return out.strip()


def main() -> int:
    bundle_path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUNDLE)
    raw = bundle_path.read_text()
    blocks = re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", raw, re.S)

    found: dict[str, str] = {}
    for block in blocks:
        subj = subject(block)
        for name in WANTED:
            if name in subj and name not in found:
                found[name] = block.strip()

    missing = [n for n in WANTED if n not in found]
    if missing:
        print(f"ERROR: missing roots in {bundle_path}: {missing}", file=sys.stderr)
        return 1

    lines: list[str] = []
    for name in WANTED:
        lines.append(f"    // ---- {name} ----")
        for line in found[name].splitlines():
            lines.append(f'    "{line}\\n"')
    body = "\n".join(lines)

    OUT.write_text(HEADER.format(body=body))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(WANTED)} roots)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
