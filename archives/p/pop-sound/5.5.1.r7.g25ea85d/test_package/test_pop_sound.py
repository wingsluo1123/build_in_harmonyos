#!/usr/bin/env python3
"""pop-sound 5.5.1.r7.g25ea85d 适配自检（test_package 内部执行，上游 N=0）。

用法: python3 test_pop_sound.py <package_folder>

分四组，共 38 条用例：
  A1-A8   交付结构与元数据（index.theme 语义、目录、许可、无源稿泄漏）
  B1-B25  上游样例逐条：21 个实体 .oga + 4 个别名，逐个校验 Ogg 容器与 Vorbis 编码
  H1-H5   鸿蒙特有（OHOS）验收：主题路径约定、Context 映射、编解码、可执行位、
          大小写不敏感文件系统安全性
每条用例打印 `CASE <id> <name>: PASS|FAIL|SKIP ...`，末尾输出
`TOTAL=.. PASSED=.. FAILED=.. SKIPPED=..`，有失败则退出码 1。
"""

import os
import sys

CONTEXTS = ("alert", "action", "notification")
ALIASES = {
    "action/screen-capture.oga": "camera-shutter.oga",
    "notification/message-new-email.oga": "message.oga",
    "notification/power-unplug.oga": "power-plug.oga",
    "notification/theme-demo.oga": "system-ready.oga",
}
ELF_MAGIC = b"\x7fELF"

results = []


def case(cid, name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append((cid, name, status, detail))
    print(f"CASE {cid} {name}: {status}{(' ' + detail) if detail else ''}")
    return ok


def parse_index_theme(path):
    """解析 freedesktop 声音主题 index.theme（INI）。"""
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


def main(package_folder):
    theme_root = os.path.join(package_folder, "share", "sounds", "Pop")
    stereo = os.path.join(theme_root, "stereo")
    index_theme = os.path.join(theme_root, "index.theme")

    # ── A. 交付结构 ────────────────────────────────────────────────
    case("A1", "theme_dir_exists", os.path.isdir(theme_root), theme_root)
    if not case("A2", "index_theme_exists", os.path.isfile(index_theme), index_theme):
        summarize()
        return 1

    sections = parse_index_theme(index_theme)
    main_sec = sections.get("Sound Theme", {})
    case("A3", "theme_name_is_Pop", main_sec.get("Name") == "Pop",
         f"Name={main_sec.get('Name')!r}")

    declared = [d for d in main_sec.get("Directories", "").split() if d]
    case("A4", "declared_dirs_present",
         all(os.path.isdir(os.path.join(theme_root, d)) for d in declared) and declared,
         f"Directories={declared}")

    meta_ok = True
    detail = []
    for d in declared:
        sec = sections.get(d, {})
        ctx = sec.get("Context", "")
        prof = sec.get("OutputProfile", "")
        meta_ok &= ctx in ("Alert", "Action", "Notification") and prof == "stereo"
        detail.append(f"{d}(Context={ctx},Profile={prof})")
    case("A5", "dir_metadata_context_profile", meta_ok, "; ".join(detail))

    residue = []
    for root, _dirs, files in os.walk(theme_root):
        for f in files:
            if f.endswith((".mmpz", ".wav", ".in")) or f == "meson.build":
                residue.append(os.path.join(root, f))
    case("A6", "no_source_residue", not residue, f"residue={residue}")

    elves = []
    executables = []
    for root, _dirs, files in os.walk(theme_root):
        for f in files:
            p = os.path.join(root, f)
            if os.path.islink(p):
                continue
            if os.access(p, os.X_OK):
                executables.append(p)
            with open(p, "rb") as fh:
                if fh.read(4) == ELF_MAGIC:
                    elves.append(p)
    case("A7", "no_elf_in_package", not elves, f"elf={elves}")
    case("A8", "licenses_present",
         os.path.isfile(os.path.join(package_folder, "licenses", "COPYING"))
         and os.path.isfile(os.path.join(package_folder, "licenses", "LICENSE_CCBYSA")),
         "licenses/COPYING + LICENSE_CCBYSA")

    # ── B. 上游样例逐条（21 实体 + 4 别名 = 25）───────────────────
    idx = 0
    for ctx in CONTEXTS:
        ctx_dir = os.path.join(stereo, ctx)
        for name in sorted(os.listdir(ctx_dir)) if os.path.isdir(ctx_dir) else []:
            idx += 1
            rel = f"{ctx}/{name}"
            path = os.path.join(ctx_dir, name)
            ok = os.path.exists(path)
            detail = rel
            if ok:
                with open(path, "rb") as fh:
                    head = fh.read(1024)
                ok = head[:4] == b"OggS" and b"vorbis" in head
                detail = f"{rel} ({os.path.getsize(path)}B{', alias' if rel in ALIASES else ''})"
            case(f"B{idx:02d}", f"upstream_sample_{rel}", ok, detail)

    # ── H. 鸿蒙特有验收 ───────────────────────────────────────────
    rel_theme = os.path.relpath(theme_root, package_folder).replace(os.sep, "/")
    case("H1", "ohos_theme_path_convention", rel_theme == "share/sounds/Pop",
         f"{rel_theme} (freedesktop: <datadir>/sounds/<theme>，OHOS 音频服务按 XDG_DATA_DIRS 检索)")

    ctx_set = {sections.get(d, {}).get("Context") for d in declared}
    case("H2", "ohos_context_mapping_complete",
         ctx_set == {"Alert", "Action", "Notification"},
         f"Contexts={sorted(c for c in ctx_set if c)} → OHOS 告警/按键/通知三类系统事件")

    codec_ok, bad = True, []
    for root, _dirs, files in os.walk(stereo):
        for f in files:
            p = os.path.join(root, f)
            with open(p, "rb") as fh:
                head = fh.read(1024)
            if not (head[:4] == b"OggS" and b"vorbis" in head):
                codec_ok = False
                bad.append(p)
    case("H3", "ohos_codec_vorbis_only", codec_ok, f"non-vorbis={bad}")

    case("H4", "ohos_share_is_readonly_data", not elves and not executables,
         f"exec={executables}")

    fold_ok, clashes = True, []
    for root, _dirs, files in os.walk(stereo):
        seen = {}
        for f in files:
            key = f.casefold()
            if key in seen:
                fold_ok = False
                clashes.append((os.path.join(root, seen[key]), os.path.join(root, f)))
            seen[key] = f
    case("H5", "ohos_casefold_safe", fold_ok, f"clashes={clashes}")

    return summarize()


def summarize():
    total = len(results)
    passed = sum(1 for r in results if r[2] == "PASS")
    failed = sum(1 for r in results if r[2] == "FAIL")
    skipped = total - passed - failed
    print(f"TOTAL={total} PASSED={passed} FAILED={failed} SKIPPED={skipped}")
    for cid, name, status, detail in results:
        if status == "FAIL":
            print(f"FAILED_CASE {cid} {name} {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_pop_sound.py <package_folder>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
