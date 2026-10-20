#!/usr/bin/env python3
"""pop-sound 消费端用例：按 freedesktop Sound Theme 规范消费已安装的主题。

用法: python3 consumer_soundtheme.py <package_folder>

流程（与 libcanberra / OHOS 声音服务的检索方式一致）：
  1) 以 <package_folder>/share 作为 XDG_DATA_DIRS 候选，定位 sounds/<theme>；
  2) 解析 index.theme：Directories= 给出 <profile>/<context> 列表，OutputProfile 选 profile；
  3) 按事件名在各 context 目录里解析 <name>.oga（含别名事件，alias > entity 见 README）；
  4) 实际打开并读取每个事件的头部字节（"播放"路径的最小可用替代：容器必须可读）。

输出 `CASE C<id> <event>: PASS|FAIL ...`，末尾 `TOTAL=.. PASSED=.. FAILED=.. SKIPPED=..`。
"""

import os
import sys

EVENTS = [
    ("C1", "bell"),
    ("C2", "message"),
    ("C3", "complete"),
    ("C4", "battery-low"),
    ("C5", "alarm-clock-elapsed"),
    ("C6", "system-shutdown"),
    ("C7", "camera-shutter"),
    ("C8", "audio-volume-change"),
    ("C9", "message-new-email"),      # README: message > message-new-email（别名）
    ("C10", "screen-capture"),        # README: camera-shutter > screen-capture（别名）
    ("C11", "power-unplug"),          # README: power-plug > power-unplug（别名）
    ("C12", "theme-demo"),            # README: system-ready > theme-demo（别名）
]


def parse_index_theme(path):
    sections, cur = {}, None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                cur = line[1:-1]
                sections[cur] = {}
            elif "=" in line and cur is not None:
                k, v = line.split("=", 1)
                sections[cur][k.strip()] = v.strip()
    return sections


def locate_theme(datadir):
    """freedesktop: $XDG_DATA_DIRS/sounds/<theme>/index.theme"""
    sounds = os.path.join(datadir, "sounds")
    if not os.path.isdir(sounds):
        return None, None
    for theme in sorted(os.listdir(sounds)):
        index = os.path.join(sounds, theme, "index.theme")
        if os.path.isfile(index):
            return theme, os.path.join(sounds, theme)
    return None, None


def main(package_folder):
    passed = 0
    failed = 0
    datadir = os.path.join(package_folder, "share")
    theme, theme_root = locate_theme(datadir)
    if not theme_root:
        print(f"CASE C0 locate_theme: FAIL datadir={datadir}")
        print(f"TOTAL={len(EVENTS) + 1} PASSED=0 FAILED=1 SKIPPED={len(EVENTS)}")
        return 1
    print(f"CASE C0 locate_theme: PASS theme={theme} root={theme_root}")
    passed += 1

    sections = parse_index_theme(os.path.join(theme_root, "index.theme"))
    dirs = [d for d in sections.get("Sound Theme", {}).get("Directories", "").split() if d]
    contexts = [d.split("/", 1)[1] for d in dirs if "/" in d]

    for cid, event in EVENTS:
        found = None
        for ctx in contexts:
            cand = os.path.join(theme_root, "stereo", ctx, f"{event}.oga")
            if os.path.exists(cand):
                found = cand
                break
        if not found:
            print(f"CASE {cid} {event}: FAIL not found in {contexts}")
            failed += 1
            continue
        try:
            with open(found, "rb") as fh:
                head = fh.read(1024)
            ok = head[:4] == b"OggS" and b"vorbis" in head
            print(f"CASE {cid} {event}: {'PASS' if ok else 'FAIL'} "
                  f"{os.path.relpath(found, theme_root)} ({os.path.getsize(found)}B)")
            passed += 1 if ok else 0
            failed += 0 if ok else 1
        except OSError as e:
            print(f"CASE {cid} {event}: FAIL unreadable {found}: {e}")
            failed += 1

    total = passed + failed
    print(f"TOTAL={total} PASSED={passed} FAILED={failed} SKIPPED=0")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: consumer_soundtheme.py <package_folder>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
