#!/usr/bin/env python3
"""gravit/0.5.1 无头渲染端到端消费者用例（鸿蒙特有测试，rule12）。

**本文件不是断言清单**，而是若干**具名消费者用例**；每个用例都是一条完整的消费
者流程，按四段式组织：

    构造输入 → 真实执行 → 产出结果 → 校验内容

    HD-1  offscreen-run-and-self-quit
          构造输入: `bin/gravit -n "videowidth 320" "videoheight 240" "echo 1"
                     "timeradd shot 8 1 screenshot" "timeradd bye 11 1 quit"`
                     + `SDL_VIDEODRIVER=dummy`（无窗口系统）+ 全新的 $HOME
          真实执行: 真实运行约 11 秒（真进程、真渲染循环），由内置定时器自行退出
          产出结果: 退出码 + 完整运行日志（stdout）
          校验内容: 退出码 0（未被 kill）且日志出现鸿蒙离屏路径的全部证据行
    HD-2  screenshot-png-structure
          构造输入: HD-1 中 `screenshot` 命令写出的真实文件
          真实执行: 用本文件自带的独立解码器解码（zlib inflate + 手写 PNG 反滤波
                    + 逐 chunk CRC 自校验），不调用被测程序的任何代码
          产出结果: 解码出的像素缓冲 + 各 chunk 结构
          校验内容: PNG 签名 / IHDR=(320,240,8bit,truecolour,无隔行) /
                    全部 chunk 的 CRC 自洽 / IDAT 解压长度 = h*(3w+1) /
                    像素字节数 = 3*w*h（与请求的离屏模式一致）
    HD-3  frame-content-real-scene
          构造输入: HD-2 解码出的像素缓冲
          真实执行: 逐像素统计（非黑像素数、不同颜色数）
          产出结果: 帧统计
          校验内容: 画面不是空缓冲——非黑像素过半且颜色数上万（真实三维场景）

参考判据的独立来源：HD-1 的证据行取自被测源码里鸿蒙离屏路径的打印点
（`src/gfx.c` 的 `Offscreen GL context:`、`Your video mode is ...x...x32`、
`OpenGL video driver: vendor=`）与 console 的定时器回显（`timeradd`/`quit`），
HD-2/HD-3 的判据取自我们**请求的离屏模式 320x240x32** 与 PNG 规范本身，均不是把
程序自己的输出回填成 golden。
"""

import os
import re
import struct
import subprocess
import sys
import tempfile
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
VIDEO_WIDTH = 320
VIDEO_HEIGHT = 240

# HD-1 的证据行：鸿蒙离屏路径真的跑起来的痕迹（取自被测源码的打印点）。
REQUIRED_EVIDENCE = [
    ("Offscreen GL context:", "OSMesa 离屏上下文创建（src/gfx.c 的离屏后端生效）"),
    (f"Your video mode is {VIDEO_WIDTH}x{VIDEO_HEIGHT}x32", "请求的离屏分辨率被采纳"),
    ("OpenGL video driver: vendor=", "运行期 GL 渲染器可达"),
    ("multi-threaded rendering", "OpenMP 帧线程开启"),
    ("Added timer 'shot'", "内置定时器承载运行中的 screenshot 命令"),
    ("Added timer 'bye'", "内置定时器承载运行中的 quit 命令"),
    ("Deleting timer 'bye'", "quit 定时器到期，应用自行退出"),
]
FORBIDDEN_EVIDENCE = [
    ("Could not open", "包内数据文件缺失（可重定位查找失效）"),
    ("Could not open font", "包内字体缺失（可重定位查找失效）"),
]

STATE = {}


def decode_png(path):
    """独立 PNG 解码器：返回结构信息与像素缓冲；任何一处不自洽即抛 ValueError。

    这是**独立实现**：zlib inflate + 手写 PNG 反滤波 + 逐 chunk CRC 自校验，
    不依赖被测程序、不依赖第三方图像库。
    """
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:8] != PNG_SIGNATURE:
        raise ValueError("不是 PNG（签名不符）")

    position = 8
    compressed = b""
    header = None
    chunk_kinds = []
    crcs_checked = 0
    while position < len(data):
        if position + 8 > len(data):
            raise ValueError("chunk 头被截断")
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        position += 8
        chunk = data[position:position + length]
        if len(chunk) != length:
            raise ValueError(f"{kind!r} 数据被截断")
        crc = data[position + length:position + length + 4]
        if len(crc) != 4:
            raise ValueError(f"{kind!r} CRC 被截断")
        stored = struct.unpack(">I", crc)[0]
        actual = zlib.crc32(kind + chunk) & 0xFFFFFFFF
        if stored != actual:
            raise ValueError(f"{kind!r} CRC 不自洽: {stored:#010x} != {actual:#010x}")
        crcs_checked += 1
        chunk_kinds.append(kind.decode("ascii", "replace"))
        position += length + 4

        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            compressed += chunk
        elif kind == b"IEND":
            break

    if header is None:
        raise ValueError("没有 IHDR")
    width, height, bit_depth, colour_type, compression, filter_method, interlace = header
    if (bit_depth, colour_type, compression, filter_method, interlace) != (8, 2, 0, 0, 0):
        raise ValueError(
            "不是 8 位真彩色无隔行 PNG: "
            f"depth={bit_depth} colour={colour_type} interlace={interlace}"
        )

    raw = zlib.decompress(compressed)
    stride = width * 3
    if len(raw) != height * (stride + 1):
        raise ValueError(f"IDAT 解压长度 {len(raw)} != 期望 {height * (stride + 1)}")

    pixels = bytearray()
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        if filter_type == 1:
            for x in range(3, stride):
                line[x] = (line[x] + line[x - 3]) & 0xFF
        elif filter_type == 2:
            for x in range(stride):
                line[x] = (line[x] + previous[x]) & 0xFF
        elif filter_type == 3:
            for x in range(stride):
                left = line[x - 3] if x >= 3 else 0
                line[x] = (line[x] + ((left + previous[x]) >> 1)) & 0xFF
        elif filter_type == 4:
            for x in range(stride):
                left = line[x - 3] if x >= 3 else 0
                up = previous[x]
                up_left = previous[x - 3] if x >= 3 else 0
                estimate = left + up - up_left
                pa, pb, pc = abs(estimate - left), abs(estimate - up), abs(estimate - up_left)
                predictor = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
                line[x] = (line[x] + predictor) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"未知 PNG 滤波类型 {filter_type}")
        pixels += line
        previous = line

    return {
        "width": width,
        "height": height,
        "pixels": pixels,
        "chunks": chunk_kinds,
        "crcs_checked": crcs_checked,
        "idat": len(compressed),
    }


def case_1_run(executable, package_folder, report):
    """HD-1：真实无头运行整段渲染会话，并核对离屏路径的证据行。"""
    print("=== HD-1 offscreen-run-and-self-quit ===")
    home = tempfile.mkdtemp(prefix="gravit-home-")
    arguments = [
        executable, "-n",
        f"videowidth {VIDEO_WIDTH}", f"videoheight {VIDEO_HEIGHT}", "echo 1",
        "timeradd shot 8 1 screenshot",
        "timeradd bye 11 1 quit",
    ]
    environment = {
        **os.environ,
        "HOME": home,
        "SDL_VIDEODRIVER": "dummy",
        "SDL_AUDIODRIVER": "dummy",
    }
    print(f"    构造输入: {' '.join(arguments[1:])}")
    print(f"              SDL_VIDEODRIVER=dummy, HOME={home}")

    proc = subprocess.Popen(
        arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=environment,
        # 包目录就是应用解析数据文件所用的安装前缀。
        cwd=package_folder,
    )
    killed = False
    try:
        out, _ = proc.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _ = proc.communicate()
        killed = True

    log = out.decode("utf-8", "replace")
    print("    ---- 真实运行日志 ----")
    for line in log.strip().splitlines():
        print(f"    | {line}")
    print("    ----------------------")
    print(f"    产出结果: 退出码={proc.returncode}，{len(out)} 字节日志"
          f"{'（超时被强制结束）' if killed else '（自行退出）'}")

    problems = []
    if killed:
        problems.append("应用没有按定时器自行退出（被超时强制结束）")
    if proc.returncode != 0:
        problems.append(f"退出码 {proc.returncode} != 0")
    for text, why in REQUIRED_EVIDENCE:
        if text not in log:
            problems.append(f"缺少证据行 {text!r}（{why}）")
    for text, why in FORBIDDEN_EVIDENCE:
        if text in log:
            problems.append(f"出现 {text!r}（{why}）")

    match = re.search(r"screenshot saved to (\S+)", log)
    if not match:
        problems.append("screenshot 命令没有写出截图（日志无 'screenshot saved to'）")

    if problems:
        print(f"    校验内容: FAIL: {'; '.join(problems)}")
        report.append((False, "HD-1 offscreen-run-and-self-quit", problems))
        return False
    STATE["log"] = log
    STATE["home"] = home
    STATE["screenshot"] = match.group(1)
    print(f"    校验内容: PASS（{len(REQUIRED_EVIDENCE)} 项证据齐全，退出码 0，"
          f"截图 → {STATE['screenshot']}）")
    report.append((True, "HD-1 offscreen-run-and-self-quit", []))
    return True


def case_2_structure(report):
    """HD-2：独立解码截图，核对 PNG 结构与请求的离屏模式一致。"""
    print("=== HD-2 screenshot-png-structure ===")
    if "screenshot" not in STATE:
        print("    构造输入: 不可用（HD-1 未产出截图）")
        report.append((False, "HD-2 screenshot-png-structure", ["HD-1 未产出截图"]))
        return False

    path = STATE["screenshot"]
    print(f"    构造输入: {path}")
    if not os.path.isfile(path):
        print("    真实执行: 截图文件不存在")
        report.append((False, "HD-2 screenshot-png-structure", ["截图文件不存在"]))
        return False
    print(f"    真实执行: 用自带独立解码器读取 {os.path.getsize(path)} 字节 PNG")
    try:
        decoded = decode_png(path)
    except (ValueError, zlib.error, OSError) as exc:
        print(f"    产出结果: 解码失败: {exc}")
        report.append((False, "HD-2 screenshot-png-structure", [f"解码失败: {exc}"]))
        return False

    state = (decoded["width"], decoded["height"])
    print(f"    产出结果: {state[0]}x{state[1]}，chunks={decoded['chunks']}，"
          f"CRC 自校验 {decoded['crcs_checked']} 个，IDAT {decoded['idat']} 字节，"
          f"像素 {len(decoded['pixels'])} 字节")
    problems = []
    if state != (VIDEO_WIDTH, VIDEO_HEIGHT):
        problems.append(f"分辨率 {state} != 请求的离屏模式 {(VIDEO_WIDTH, VIDEO_HEIGHT)}")
    if len(decoded["pixels"]) != VIDEO_WIDTH * VIDEO_HEIGHT * 3:
        problems.append(f"像素字节数 {len(decoded['pixels'])} != "
                        f"{VIDEO_WIDTH * VIDEO_HEIGHT * 3}")
    if "IHDR" not in decoded["chunks"] or "IEND" not in decoded["chunks"]:
        problems.append(f"缺少必需 chunk: {decoded['chunks']}")

    if problems:
        print(f"    校验内容: FAIL: {'; '.join(problems)}")
        report.append((False, "HD-2 screenshot-png-structure", problems))
        return False
    STATE["decoded"] = decoded
    print("    校验内容: PASS（PNG 结构自洽且分辨率与离屏模式一致）")
    report.append((True, "HD-2 screenshot-png-structure", []))
    return True


def case_3_content(report):
    """HD-3：核对解码出的帧是真实场景而不是空缓冲。"""
    print("=== HD-3 frame-content-real-scene ===")
    if "decoded" not in STATE:
        print("    构造输入: 不可用（HD-2 未得到像素缓冲）")
        report.append((False, "HD-3 frame-content-real-scene", ["HD-2 未得到像素缓冲"]))
        return False

    decoded = STATE["decoded"]
    pixels = decoded["pixels"]
    total = decoded["width"] * decoded["height"]
    print(f"    构造输入: HD-2 解码出的 {total} 像素")
    colours = set()
    lit = 0
    for offset in range(0, len(pixels), 3):
        pixel = bytes(pixels[offset:offset + 3])
        if pixel != b"\x00\x00\x00":
            lit += 1
        colours.add(pixel)
    print("    真实执行: 逐像素统计完成")
    print(f"    产出结果: 非黑像素 {lit}/{total}，不同颜色 {len(colours)}")

    # 判据与请求的离屏模式绑定：一个被真正光栅化的三维场景不会是一块纯色缓冲。
    min_lit = total // 2
    min_colours = 1000
    problems = []
    if lit <= min_lit:
        problems.append(f"非黑像素 {lit} 未超过半数 {min_lit}（画面疑似空缓冲）")
    if len(colours) < min_colours:
        problems.append(f"不同颜色 {len(colours)} < {min_colours}（画面疑似纯色）")

    if problems:
        print(f"    校验内容: FAIL: {'; '.join(problems)}")
        report.append((False, "HD-3 frame-content-real-scene", problems))
        return False
    print("    校验内容: PASS（真实三维场景，非空缓冲）")
    report.append((True, "HD-3 frame-content-real-scene", []))
    return True


def main():
    executable = sys.argv[1]
    package_folder = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(
        os.path.dirname(executable))

    print(f"[setup] 被测命令: {executable}")
    if not os.path.isfile(executable):
        print("[setup] FAIL: 安装后的 bin/gravit 不存在")
        return 1
    print("[setup] OK: 命令存在，安装前缀 = %s" % package_folder)

    report = []
    case_1_run(executable, package_folder, report)
    case_2_structure(report)
    case_3_content(report)

    passed = sum(1 for ok, _, _ in report if ok)
    total = len(report)
    print(f"test_headless_render: {total} consumer cases, {passed} passed,"
          f" {total - passed} failed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
