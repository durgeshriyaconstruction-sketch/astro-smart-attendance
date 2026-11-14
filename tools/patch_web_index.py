#!/usr/bin/env python3
"""
Make a copy of the device dashboard (Astro.html) ready for the website.

The dashboard is the same file the ESP32 serves. For the website it needs a few
small edits so that web/supabase-bridge.js can answer its /api/... calls from
Supabase and the page tells the truth about what the website can do:

  1. load supabase-bridge.js BEFORE the app's scripts (the app starts polling
     400 ms after load, so the bridge has to be in place first)
  2-3. "device connected / failed" lights follow the real gate device's
     heartbeat instead of "the page loaded, so the device must be online"
  4. the same for the health poll and the Wi-Fi status poll
  5. skip the "share this password" dialog after adding a student: student
     sign-in passwords exist only on the device, not in the cloud
  6-10. the sign-in screen stops offering a student login. Student accounts
     live on the device; the website signs in staff (email + password) only.
     The admin hint the page already printed is left exactly as it was.

Safe to run again and again; it does nothing if the edits are already there.

    python3 tools/patch_web_index.py web/index.html
"""

import sys
from pathlib import Path

TAG = '<script src="supabase-bridge.js?v=5"></script>\n'
HOOK = "if(W.AstroWeb){W.AstroWeb.paint();return;}"

EDITS = [
    (
        "device light follows the real heartbeat (connected)",
        "function markDeviceConnected(ipHint){\n",
        "function markDeviceConnected(ipHint){\n  " + HOOK + "\n",
    ),
    (
        "device light follows the real heartbeat (failure)",
        "function markDeviceFailure(err){\n",
        "function markDeviceFailure(err){\n  " + HOOK + "\n",
    ),
    (
        "health poll does not force the device light green",
        "  DEVICE.stats={students:h.students,records:h.records,queued:h.queued,email:h.email||{}};\n}",
        "  DEVICE.stats={students:h.students,records:h.records,queued:h.queued,email:h.email||{}};\n"
        "  if(W.AstroWeb)W.AstroWeb.paint();\n}",
    ),
    (
        "Wi-Fi status poll does not invent a radio state",
        "hotspot mode';}}catch(e){}\n  renderWifiStatus();\n}",
        "hotspot mode';}}catch(e){}\n  if(W.AstroWeb)W.AstroWeb.paint();\n  renderWifiStatus();\n}",
    ),
    (
        "no password dialog on the website",
        "    setTimeout(function(){\n      modal({\n        title:'Student created',",
        "    if(!(res&&res.web))setTimeout(function(){\n      modal({\n        title:'Student created',",
    ),
    (
        "sign-in: the name field asks for an email",
        '<label>Email or full name</label>\n        <div class="inp-ico"><span id="ic-user"></span>',
        '<label>Email</label>\n        <div class="inp-ico"><span id="ic-user"></span>',
    ),
    (
        "sign-in: placeholder without 'or student name'",
        'id="login-id" type="text" placeholder="astro@gmail.com \u00b7 or student name"',
        'id="login-id" type="text" placeholder="astro@gmail.com"',
    ),
    (
        "sign-in: hint says who can sign in here",
        "One login for everyone \u2014 admins sign in with email, students with their registered name.",
        "Staff sign in here with their email. Student sign-in is on the school device, not on this website.",
    ),
    (
        "sign-in: password hint without the student default",
        "Admin: your password \u00b7 Student: your password (default: your sign-in number, e.g. 1005).",
        "The password of your staff account.",
    ),
    (
        "sign-in: no 'Fill Student' shortcut",
        '<b class="mono">admin123</b> \u00b7 Students sign in with the name and password you give them.&nbsp;\n'
        '        <a href="javascript:void(0)" style="font-weight:700" onclick="fillDemo(\'admin\')">Fill Admin</a>'
        ' \u00b7 <a href="javascript:void(0)" style="font-weight:700" onclick="fillDemo(\'student\')">Fill Student (Shaurya \u00b7 1001)</a></div>',
        '<b class="mono">admin123</b> \u00b7&nbsp;\n'
        '        <a href="javascript:void(0)" style="font-weight:700" onclick="fillDemo(\'admin\')">Fill Admin</a></div>',
    ),
]


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "web/index.html")
    html = path.read_text(encoding="utf-8")
    changed = []

    # 1. the bridge script tag: exactly one, in front of the first app script
    import re

    html_no_tag, removed = re.subn(r'<script src="supabase-bridge\.js[^"]*"></script>\n?', "", html)
    first = html_no_tag.find("<script>")
    if first < 0:
        print("error: no <script> block found - is this the dashboard file?")
        return 1
    with_tag = html_no_tag[:first] + TAG + html_no_tag[first:]
    if with_tag != html:
        changed.append("bridge script tag placed before the app scripts")
    html = with_tag

    for name, old, new in EDITS:
        if new in html:
            continue
        if html.count(old) != 1:
            print(f"error: expected exactly one place for '{name}', found {html.count(old)}")
            return 1
        html = html.replace(old, new)
        changed.append(name)

    if changed:
        path.write_text(html, encoding="utf-8")
        for c in changed:
            print("patched:", c)
    else:
        print("already patched, nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
