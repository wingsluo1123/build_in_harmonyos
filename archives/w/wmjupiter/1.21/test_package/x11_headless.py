#!/usr/bin/env python3
"""x11_headless.py — 协议级 headless X11 对端（消费者用例的「真实执行」载体）。

为什么需要它
------------
wmJupiter 是 X11 dockapp：`initXwindow()` 里 XOpenDisplay 失败即 exit(1)，而真正
体现软件功能的 `openXwindow()`（建窗口/上传 XPM/设 WM 属性）与之后的绘制主循环
（findspot → drawspot/drawmoons/数字 → copyXPMArea → RedrawWindow）在无 X server
时永远不可达。而 CI 与鸿蒙 PC 上都没有 X server：
  * archives/x/xorg-server/21.1.15 只归档了 notes.md/manifest.yaml，**没有
    conanfile.py** → 不能作为 test_package 的依赖；
  * 本机与 CI 镜像内没有任何 X server 二进制（无 Xvfb、无 Xorg）。
因此「无 display 就跑不起来」不是可以回避的点，必须真实构造执行环境。

做法
----
在测试进程内起一个真实的 X11 协议对端（127.0.0.1 TCP，DISPLAY=<host>:<n>）：
 1. 连接建立握手：success=1、1 个 screen、TrueColor 24bit 视觉、根窗口 1280x1024；
 2. 实现 wmJupiter 实际会发出的全部请求（CreateWindow / ChangeWindowAttributes /
    GetWindowAttributes / ConfigureWindow / InternAtom / GetAtomName /
    ChangeProperty / CreatePixmap / CreateGC / CreateColormap / AllocColor /
    QueryColors / QueryBestSize / PutImage / CopyArea / PolyFillRectangle /
    MapWindow / SetInputFocus / GetGeometry / GetInputFocus / QueryExtension
    + SHAPE 扩展 ShapeMask）；
 3. PutImage / CopyArea 真正落到帧缓冲上（pixmap 内部绘制 + RedrawWindow 到窗口），
    因此客户端是真的在画，而不是被"绕过"；
 4. 证据齐全后向客户端注入一个 X11 协议错误：Xlib 默认错误处理器会打印
    "X Error of failed request: ..." 并 exit(1)——这既是「客户端此刻仍在与活着的
    X server 真实对话」的证据，也保证测试在有限时间内结束、不会挂住 CI。

服务端一侧记录的证据（均为协议层原始数据，客户端无法伪造）：
  * 窗口树与几何：win / iconwin 64x64（几何串在客户端由 XWMGeometry 解析）
  * 事件掩码：CreateWindow 的 CWEventMask
  * XPM：64x64 位图经 PutImage 落到 pixmap，含 N 种不同像素值
  * Shape 掩码：ShapeMask(ShapeBounding) 对 win / iconwin 各一次
  * 主循环轮次：CopyArea(pixmap → win/iconwin) 次数 + pixmap 内部绘制算子次数
  * 渲染结果：帧缓冲中数字区/卫星区相对原始 XPM 的变化
  * WM 属性：WM_CLASS / WM_NAME / WM_COMMAND / WM_HINTS（IconWindowHint=iconwin）

线格式依据（一手取证，非推测）：
  * 应答布局按 X11 规范与 xorgproto `X11/Xproto.h` 的结构体逐字段核对
    （固定 32 字节区 + length*4 附加字节；注意 GetWindowAttributes 是 44 字节、
    length=3，GetProperty 的 format 在应答字节 1、GetGeometry 的 depth 在字节 1）；
  * 请求布局按规范逐字段核对（PutImage 的 format 在请求字节 1，不在数据区）。
"""

from __future__ import annotations

import os
import socket
import struct
import sys
import threading
import time

# ── X11 预定义原子编号（X11/Xatom.h，协议固定值） ───────────────────────────
PREDEFINED_ATOMS = {
    1: "PRIMARY", 2: "SECONDARY", 3: "ARC", 4: "ATOM", 5: "BITMAP",
    6: "CARDINAL", 7: "COLORMAP", 8: "CURSOR", 9: "CUT_BUFFER0",
    10: "CUT_BUFFER1", 11: "CUT_BUFFER2", 12: "CUT_BUFFER3", 13: "CUT_BUFFER4",
    14: "CUT_BUFFER5", 15: "CUT_BUFFER6", 16: "CUT_BUFFER7", 17: "DRAWABLE",
    18: "FONT", 19: "INTEGER", 20: "PIXMAP", 21: "POINT", 22: "RECTANGLE",
    23: "RESOURCE_MANAGER", 24: "RGB_COLOR_MAP", 25: "RGB_BEST_MAP",
    26: "RGB_BLUE_MAP", 27: "RGB_DEFAULT_MAP", 28: "RGB_GRAY_MAP",
    29: "RGB_GREEN_MAP", 30: "RGB_RED_MAP", 31: "STRING", 32: "VISUALID",
    33: "WINDOW", 34: "WM_COMMAND", 35: "WM_HINTS", 36: "WM_CLIENT_MACHINE",
    37: "WM_ICON_NAME", 38: "WM_ICON_SIZE", 39: "WM_NAME", 40: "WM_NORMAL_HINTS",
    41: "WM_SIZE_HINTS", 42: "WM_ZOOM_HINTS", 43: "MIN_SPACE", 44: "NORM_SPACE",
    45: "MAX_SPACE", 46: "END_SPACE", 47: "SUPERSCRIPT_X", 48: "SUPERSCRIPT_Y",
    49: "SUBSCRIPT_X", 50: "SUBSCRIPT_Y", 51: "UNDERLINE_POSITION",
    52: "UNDERLINE_THICKNESS", 53: "STRIKEOUT_ASCENT", 54: "STRIKEOUT_DESCENT",
    55: "ITALIC_ANGLE", 56: "X_HEIGHT", 57: "QUAD_WIDTH", 58: "WEIGHT",
    59: "POINT_SIZE", 60: "RESOLUTION", 61: "COPYRIGHT", 62: "NOTICE",
    63: "FONT_NAME", 64: "FAMILY_NAME", 65: "FULL_NAME", 66: "CAP_HEIGHT",
    67: "WM_CLASS", 68: "WM_TRANSIENT_FOR",
}

# CW* 属性位（按掩码位升序取值，规范 CreateWindow/ConfigureWindow 一致）
CW_FIELDS = [
    (0x1, "BackPixmap"), (0x2, "BackPixel"), (0x4, "BorderPixmap"),
    (0x8, "BorderPixel"), (0x10, "BitGravity"), (0x20, "WinGravity"),
    (0x40, "BackingStore"), (0x80, "BackingPlanes"), (0x100, "BackingPixel"),
    (0x200, "OverrideRedirect"), (0x400, "SaveUnder"), (0x800, "EventMask"),
    (0x1000, "DontPropagate"), (0x2000, "Colormap"), (0x4000, "Cursor"),
]

EVENT_MASK_NAMES = [
    (0x00000001, "KeyPress"), (0x00000002, "KeyRelease"),
    (0x00000004, "ButtonPress"), (0x00000008, "ButtonRelease"),
    (0x00000010, "EnterWindow"), (0x00000020, "LeaveWindow"),
    (0x00000040, "PointerMotion"), (0x00000080, "PointerMotionHint"),
    (0x00000100, "Button1Motion"), (0x00000200, "Button2Motion"),
    (0x00000400, "Button3Motion"), (0x00000800, "Button4Motion"),
    (0x00001000, "Button5Motion"), (0x00002000, "ButtonMotion"),
    (0x00004000, "KeymapState"), (0x00008000, "Exposure"),
    (0x00010000, "VisibilityChange"), (0x00020000, "StructureNotify"),
    (0x00040000, "ResizeRedirect"), (0x00080000, "SubstructureNotify"),
    (0x00100000, "SubstructureRedirect"), (0x00200000, "FocusChange"),
    (0x00400000, "PropertyChange"), (0x00800000, "ColormapChange"),
    (0x01000000, "OwnerGrabButton"),
]

OPCODES = {
    1: "CreateWindow", 2: "ChangeWindowAttributes", 3: "GetWindowAttributes",
    4: "DestroyWindow", 5: "DestroySubwindows", 6: "ChangeSaveSet",
    7: "ReparentWindow", 8: "MapWindow", 9: "MapSubwindows", 10: "UnmapWindow",
    11: "UnmapSubwindows", 12: "ConfigureWindow", 13: "CirculateWindow",
    14: "GetGeometry", 15: "QueryTree", 16: "InternAtom", 17: "GetAtomName",
    18: "ChangeProperty", 19: "DeleteProperty", 20: "GetProperty",
    21: "SetSelectionOwner", 22: "GetSelectionOwner", 23: "ConvertSelection",
    24: "SendEvent", 25: "GrabPointer", 26: "UngrabPointer", 27: "GrabButton",
    28: "UngrabButton", 29: "ChangeActivePointerGrab", 30: "GrabKeyboard",
    31: "UngrabKeyboard", 32: "GrabKey", 33: "UngrabKey", 34: "AllowEvents",
    35: "GrabServer", 36: "UngrabServer", 37: "QueryPointer",
    38: "GetMotionEvents", 39: "TranslateCoordinates", 40: "WarpPointer",
    41: "SetInputFocus", 42: "GetInputFocus", 43: "QueryKeymap", 44: "OpenFont",
    45: "CloseFont", 46: "QueryFont", 47: "QueryTextExtents", 48: "ListFonts",
    49: "ListFontsWithInfo", 50: "ListProperties", 51: "SetFontPath",
    52: "GetFontPath", 53: "CreatePixmap", 54: "FreePixmap", 55: "CreateGC",
    56: "ChangeGC", 57: "CopyGC", 58: "SetDashes", 59: "SetClipRectangles",
    60: "FreeGC", 61: "ClearArea", 62: "CopyArea", 63: "CopyPlane",
    64: "PolyPoint", 65: "PolyLine", 66: "PolySegment", 67: "PolyRectangle",
    68: "PolyArc", 69: "FillPoly", 70: "PolyFillRectangle", 71: "PolyFillArc",
    72: "PutImage", 73: "GetImage", 74: "PolyText8", 75: "PolyText16",
    76: "ImageText8", 77: "ImageText16", 78: "CreateColormap",
    79: "FreeColormap", 80: "CopyColormapAndFree", 81: "InstallColormap",
    82: "UninstallColormap", 83: "ListInstalledColormaps", 84: "AllocColor",
    85: "AllocNamedColor", 86: "AllocColorCells", 87: "AllocColorPlanes",
    88: "FreeColors", 89: "StoreColors", 90: "StoreNamedColor",
    91: "QueryColors", 92: "LookupColor", 93: "CreateCursor",
    94: "CreateGlyphCursor", 95: "FreeCursor", 96: "RecolorCursor",
    97: "QueryBestSize", 98: "QueryExtension", 99: "ListExtensions",
    100: "ChangeKeyboardMapping", 101: "GetKeyboardMapping",
    102: "ChangeKeyboardControl", 103: "GetKeyboardControl", 104: "Bell",
    105: "ChangePointerControl", 106: "GetPointerControl",
    107: "SetScreenSaver", 108: "GetScreenSaver", 109: "ChangeHosts",
    110: "ListHosts", 111: "SetAccessControl", 112: "SetCloseDownMode",
    113: "KillClient", 114: "RotateProperties", 115: "ForceScreenSaver",
    116: "SetPointerMapping", 117: "GetPointerMapping",
    118: "SetModifierMapping", 119: "GetModifierMapping",
}

# 协议常量
ROOT_WINDOW = 0x000002CA
DEFAULT_COLORMAP = 0x00000020
ROOT_VISUAL = 0x00000021
RESOURCE_ID_BASE = 0x00400000
RESOURCE_ID_MASK = 0x003FFFFF
ROOT_WIDTH, ROOT_HEIGHT = 1280, 1024
TRUE_COLOR = 4
VISUAL_CLASS_INPUT_OUTPUT = 1
ROOT_DEPTH = 24

# 应答总长恒为 32 + length*4 字节（GetWindowAttributes 例外：44 字节 / length=3）
REPLY_FIXED = 32

ERROR_BAD_IMPLEMENTATION = 17

SHAPE_MAJOR_OPCODE = 128
SHAPE_MINOR_MASK = 1
SHAPE_MINOR_RECTANGLES = 2
SHAPE_MINOR_COMBINE = 3
SHAPE_KIND_BOUNDING = 0

# 对端在连接应答中声明的扩展（Xlib 连接期缓存；实际 opcode 由 QueryExtension 给出）
EXTENSION_NAMES = ("SHAPE",)

FB_MIN_DEPTH = 24


class HeadlessXServer:
    """单客户端、协议级 headless X11 服务端（仅供消费者测试使用）。"""

    def __init__(self, display=77, host="127.0.0.1",
                 auto_stop_copies=8, auto_stop_seconds=30.0,
                 root_size=(ROOT_WIDTH, ROOT_HEIGHT), trace=None):
        self.host = host
        self.display = int(display)
        self.port = 6000 + self.display
        self.auto_stop_copies = int(auto_stop_copies)
        self.auto_stop_seconds = float(auto_stop_seconds)
        self.root_w, self.root_h = root_size
        self.trace = bool(trace) if trace is not None \
            else os.environ.get("OHC_X11_TRACE") == "1"
        self._last_req = "?"

        self._lock = threading.Lock()
        self._srv = None
        self._conn = None
        self._thread = None
        self._stop = threading.Event()
        self._dead = False

        # ── 协议状态 ──
        self.seq = 0
        self.setup_done = False
        self.next_atom_id = 200
        self.next_ext_opcode = SHAPE_MAJOR_OPCODE
        self.extensions = {}

        # ── 证据 ──
        self.requests = []               # [(seq, opcode, name)]
        self.request_counts = {}
        self.windows = {}
        self.pixmaps = {}
        self.gcs = {}
        self.colormaps = {}
        self.properties = {}             # (wid, atom 名) -> dict(type, format, n, raw)
        self.atoms = {}
        self.atom_names = {}
        self.intern_requests = []
        self.drawables = {}              # id -> dict(w, h, depth, fb)
        self.put_images = []
        self.copy_areas = []
        self.poly_fills = 0
        self.shape_masks = []
        self.mapped = []
        self.alloc_colors = []
        self.query_colors = 0
        self.input_focus_set = []
        self.errors = []

        self.started_at = None
        self.finished_at = None
        self.client_exit_reason = None

    # ────────────────────────────────────────────────────────────── 生命周期
    def start(self, bind_retries=8):
        last_err = None
        for i in range(bind_retries):
            disp = self.display + i
            port = 6000 + disp
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind((self.host, port))
                srv.listen(1)
                srv.settimeout(1.0)
            except OSError as exc:
                last_err = exc
                srv.close()
                continue
            self._srv = srv
            self.display = disp
            self.port = port
            self._thread = threading.Thread(target=self._serve, name="headless-x11")
            self._thread.daemon = True
            self.started_at = time.time()
            self._thread.start()
            return disp
        raise RuntimeError("headless X11: 无法绑定 6000+ 端口: %s" % (last_err,))

    @property
    def display_string(self):
        return "%s:%d" % (self.host, self.display)

    def stop(self):
        self._stop.set()
        for sock in (self._conn, self._srv):
            try:
                if sock is not None:
                    sock.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=5.0)

    def wait(self, max_seconds=60.0):
        deadline = time.time() + max_seconds
        while time.time() < deadline:
            if self.finished_at is not None:
                return True
            if self._thread is not None and not self._thread.is_alive():
                return True
            time.sleep(0.1)
        self.client_exit_reason = self.client_exit_reason or "timeout"
        return False

    # ─────────────────────────────────────────────────────────────── 连接处理
    def _serve(self):
        try:
            while not self._stop.is_set():
                try:
                    conn, _addr = self._srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                self._conn = conn
                conn.settimeout(1.0)
                try:
                    self._handle_client(conn)
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    self._conn = None
                self.finished_at = time.time()
                break
        except Exception as exc:
            with self._lock:
                self.errors.append("server: %r" % (exc,))
        finally:
            try:
                self._srv.close()
            except Exception:
                pass

    def _handle_client(self, conn):
        if not self._handshake(conn):
            return
        self.setup_done = True
        buf = b""
        while not self._stop.is_set() and not self._dead:
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                self._maybe_finish()
                continue
            except OSError:
                break
            if not chunk:
                self.client_exit_reason = self.client_exit_reason or "client_closed"
                break
            buf += chunk
            buf = self._consume(buf)
            self._maybe_finish()

    def _handshake(self, conn):
        buf = b""
        while len(buf) < 12:
            try:
                chunk = conn.recv(4096)
            except (socket.timeout, OSError):
                return False
            if not chunk:
                return False
            buf += chunk
        if buf[0:1] != b"l":
            # 客户端声明 MSB-first；arm64/x86 上不应出现，明确拒绝而非静默错解
            self.errors.append("client byte order %r unsupported" % (buf[0:1],))
            return False
        name_len, data_len = struct.unpack_from("<HH", buf, 6)
        total = 12 + ((name_len + data_len + 3) // 4) * 4
        while len(buf) < total:
            try:
                chunk = conn.recv(4096)
            except (socket.timeout, OSError):
                return False
            if not chunk:
                return False
            buf += chunk
        conn.sendall(self._build_setup_reply())
        return True

    def _build_setup_reply(self):
        vendor = b"AtomCode headless X11 protocol peer"
        vendor += b"\x00" * (-len(vendor) % 4)
        formats = (bytes([1, 1, 32]) + b"\x00" * 5
                   + bytes([24, 32, 32]) + b"\x00" * 5
                   + bytes([32, 32, 32]) + b"\x00" * 5)
        screen = struct.pack(
            "<IIIIIHHHHHHIBBBB",
            ROOT_WINDOW, DEFAULT_COLORMAP, 0xFFFFFF, 0x000000, 0,
            self.root_w, self.root_h, 325, 244, 1, 1,
            ROOT_VISUAL, 0, 0, ROOT_DEPTH, 1,
        )
        depths = struct.pack("<BBHI", ROOT_DEPTH, 0, 1, 0) + struct.pack(
            "<IBBHIIII", ROOT_VISUAL, TRUE_COLOR, 8, 256,
            0x00FF0000, 0x0000FF00, 0x000000FF, 0)
        # 注意：setup 应答里不得带扩展名列表——libX11 的 XOpenDisplay 解析器
        # （OpenDis.c）按 usedbytes == setuplength 严格校验且不消费扩展区，
        # 多写 4 字节即报 "Did not parse entire setup message"。
        # 扩展可见性改由 ListExtensions 应答提供（xcb 的 xcb_get_extension_data 走这条路）。
        extra = vendor + formats + screen + depths
        # setup 头部固定 40 字节；length 字段按 xcb 口径统计字节 8 起的总长约 4 字节单位
        setup_len = (32 + len(extra)) // 4
        header = struct.pack(
            "<BBHHIIIIHH", 1, 0, 11, 0, setup_len,
            12101015, RESOURCE_ID_BASE, RESOURCE_ID_MASK, 256, len(vendor),
        )
        header += struct.pack("<H", 65535)          # 26-27 最大请求长度（4 字节单位）
        header += bytes([1, 3, 0, 0, 32, 32, 8, 255])   # 28-35 屏数/格式数/字节序…
        header += struct.pack("<I", 0)              # 36-39 保留
        return header + extra

    def _consume(self, buf):
        while len(buf) >= 4:
            opcode = buf[0]
            total = struct.unpack_from("<H", buf, 2)[0] * 4
            if total < 4 or total % 4:
                self.errors.append("bad request length %d (opcode %d)" % (total, opcode))
                self._dead = True
                return b""
            if len(buf) < total:
                return buf
            packet = buf[:total]
            buf = buf[total:]
            self.seq += 1
            self._dispatch(opcode, packet)
        return buf

    def _dispatch(self, opcode, packet):
        if opcode in OPCODES:
            name = OPCODES[opcode]
        elif opcode >= 128:
            index = opcode - 128
            names = [n for n, op in sorted(self.extensions.items(), key=lambda kv: kv[1])]
            name = "EXT:%s" % (names[index] if index < len(names) else index)
        else:
            name = "opcode-%d" % opcode
        self.request_counts[name] = self.request_counts.get(name, 0) + 1
        self.requests.append((self.seq, opcode, name))
        self._last_req = "%s(op=%d seq=%d)" % (name, opcode, self.seq)
        if self.trace:
            sys.stderr.write("[x11] REQ  %-24s op=%-3d seq=%d len=%d head=%s\n"
                             % (name, opcode, self.seq, len(packet),
                                packet[:24].hex()))
            sys.stderr.flush()
        try:
            handler = getattr(self, "_req_%d" % opcode, None)
            if handler is not None:
                handler(packet)
        except Exception as exc:
            self.errors.append("dispatch %s: %r" % (name, exc))

    # ── 应答构造（固定 32 字节区 + extra；length = len(extra)//4） ──
    def _reply(self, area=b"", extra=b"", detail=0, sequence=None):
        if len(area) > 24:
            raise ValueError("reply area too long: %d" % len(area))
        area = area + b"\x00" * (24 - len(area))
        buf = bytearray(REPLY_FIXED) + bytearray(extra)
        buf[0] = 1
        buf[1] = detail & 0xFF
        struct.pack_into("<H", buf, 2, (self.seq if sequence is None else sequence) & 0xFFFF)
        struct.pack_into("<I", buf, 4, len(extra) // 4)
        buf[8:REPLY_FIXED] = area
        if self.trace:
            sys.stderr.write("[x11] RPLY %-24s area=%d extra=%d length=%d total=%d\n"
                             % (self._last_req, len(area), len(extra),
                                len(extra) // 4, REPLY_FIXED + len(extra)))
            sys.stderr.flush()
        self._send(bytes(buf))

    def _send(self, data):
        with self._lock:
            conn = self._conn
        if conn is None:
            return
        try:
            conn.sendall(data)
        except OSError:
            self._dead = True

    # ── 请求处理器（偏移量均按协议规范，packet 含 4 字节请求头） ───────────
    def _req_1(self, packet):                                     # CreateWindow
        (wid, parent, x, y, w, h, border, cls, visual, mask) = struct.unpack_from(
            "<IIhhHHHHII", packet, 4)
        values = self._parse_cw_values(mask, packet, 32)
        parent_win = self.windows.get(parent)
        depth = parent_win["depth"] if parent_win else ROOT_DEPTH
        if not visual:
            visual = parent_win["visual"] if parent_win else ROOT_VISUAL
        self.windows[wid] = {
            "id": wid, "parent": parent, "x": x, "y": y, "width": w, "height": h,
            "border": border, "class": cls, "visual": visual, "depth": depth,
            "values": values, "mapped": False, "colormap": DEFAULT_COLORMAP,
            "override_redirect": bool(values.get("OverrideRedirect", 0)),
            "order": len(self.windows),
        }
        self._ensure_drawable(wid, w, h, depth)

    def _req_2(self, packet):                        # ChangeWindowAttributes
        wid, mask = struct.unpack_from("<II", packet, 4)
        values = self._parse_cw_values(mask, packet, 12)
        win = self.windows.get(wid)
        if win is not None:
            win.setdefault("attr_changes", []).append(values)
            if "Colormap" in values:
                win["colormap"] = values["Colormap"]
            if "OverrideRedirect" in values:
                win["override_redirect"] = bool(values["OverrideRedirect"])

    def _req_3(self, packet):                              # GetWindowAttributes
        wid = struct.unpack_from("<I", packet, 4)[0]
        win = self.windows.get(wid)
        if win is None:
            visual, cmap = ROOT_VISUAL, DEFAULT_COLORMAP
            mapped, override = 1, 0
        else:
            visual = win["visual"]
            cmap = win.get("colormap", DEFAULT_COLORMAP)
            mapped = 1 if win["mapped"] else 0
            override = 1 if win.get("override_redirect") else 0
        area = struct.pack("<IHBBIIBBBB", visual, VISUAL_CLASS_INPUT_OUTPUT, 0, 0,
                           0xFFFFFFFF, 0, 0, mapped, 2 if mapped else 0, override) \
            + struct.pack("<I", cmap)
        # 附加 12 字节：allEventMasks / yourEventMask / doNotPropagateMask / pad
        self._reply(area, struct.pack("<IIHH", 0, 0, 0, 0))

    def _req_4(self, packet):                                       # DestroyWindow
        wid = struct.unpack_from("<I", packet, 4)[0]
        self.windows.pop(wid, None)
        self.drawables.pop(wid, None)

    def _req_8(self, packet):                                          # MapWindow
        wid = struct.unpack_from("<I", packet, 4)[0]
        win = self.windows.get(wid)
        if win is not None:
            win["mapped"] = True
        self.mapped.append(wid)

    def _req_10(self, packet):                                       # UnmapWindow
        wid = struct.unpack_from("<I", packet, 4)[0]
        win = self.windows.get(wid)
        if win is not None:
            win["mapped"] = False

    def _req_12(self, packet):                                    # ConfigureWindow
        wid, mask = struct.unpack_from("<IH", packet, 4)
        win = self.windows.get(wid)
        if win is None:
            return
        values = self._parse_cw_values(mask, packet, 12)
        for low, key in (("width", "width"), ("height", "height"), ("x", "x"),
                         ("y", "y"), ("border", "border")):
            if key in values:
                win[low] = struct.unpack("<h", struct.pack("<I", values[key]))[0] \
                    if key in ("x", "y") else values[key]

    def _req_14(self, packet):                                       # GetGeometry
        did = struct.unpack_from("<I", packet, 4)[0]
        if did == ROOT_WINDOW:
            depth, root, x, y, w, h, border = (ROOT_DEPTH, ROOT_WINDOW, 0, 0,
                                               self.root_w, self.root_h, 0)
        else:
            win, pix = self.windows.get(did), self.pixmaps.get(did)
            if win is not None:
                depth, root = win["depth"], ROOT_WINDOW
                x, y, w, h, border = (win["x"], win["y"], win["width"],
                                      win["height"], win["border"])
            elif pix is not None:
                depth, root = pix["depth"], pix["root"]
                x, y, border = 0, 0, 0
                w, h = pix["width"], pix["height"]
            else:
                depth, root, x, y, w, h, border = ROOT_DEPTH, ROOT_WINDOW, 0, 0, 0, 0, 0
        # depth 在应答字节 1；固定区从偏移 8 起为 root/x/y/w/h/border
        self._reply(struct.pack("<IHHHHH", root, x, y, w, h, border), detail=depth)

    def _req_16(self, packet):                                       # InternAtom
        n = struct.unpack_from("<H", packet, 6)[0]
        name = packet[8:8 + n].decode("latin-1")
        atom = self.atoms.get(name)
        if atom is None:
            atom = self.next_atom_id
            self.next_atom_id += 1
            self.atoms[name] = atom
            self.atom_names[atom] = name
        self.intern_requests.append(name)
        self._reply(struct.pack("<I", atom))

    def _req_17(self, packet):                                       # GetAtomName
        atom = struct.unpack_from("<I", packet, 4)[0]
        name = self.atom_names.get(atom, PREDEFINED_ATOMS.get(atom, "")).encode("latin-1")
        padded = name + b"\x00" * (-len(name) % 4)
        self._reply(struct.pack("<H", len(name)), extra=padded)

    def _req_18(self, packet):                                    # ChangeProperty
        wid, prop, ptype, fmt = struct.unpack_from("<IIIB", packet, 4)
        n = struct.unpack_from("<I", packet, 20)[0]
        unit = {8: 1, 16: 2, 32: 4}[fmt]
        raw = packet[24:24 + n * unit]
        self.properties[(wid, self._atom_name(prop))] = {
            "type": self._atom_name(ptype), "format": fmt,
            "nelements": n, "raw": raw,
        }

    def _req_20(self, packet):                                       # GetProperty
        wid, prop = struct.unpack_from("<II", packet, 4)
        rec = self.properties.get((wid, self._atom_name(prop)))
        if rec is None:
            self._reply(struct.pack("<III", 0, 0, 0), detail=0)
            return
        raw = rec["raw"]
        self._reply(struct.pack("<III", self.atoms.get(rec["type"], 0), 0,
                                rec["nelements"]), extra=raw, detail=rec["format"])

    def _req_41(self, packet):                                     # SetInputFocus
        focus, revert, ts = struct.unpack_from("<IBI", packet, 4)
        self.input_focus_set.append({"focus": focus, "revert": revert, "time": ts})

    def _req_42(self, packet):                                     # GetInputFocus
        self._reply(struct.pack("<I", 1))

    def _req_43(self, packet):                                       # QueryKeymap
        self._reply(struct.pack("<IIIIIIII", 0, 0, 0, 0, 0, 0, 0, 0))

    def _req_53(self, packet):                                      # CreatePixmap
        # 权威线格式：depth 在请求字节 1（实测包头 3518 0400 b8000000 ca020000 → depth=0x18=24，
        # 请求全长 16 字节），不在数据区末尾
        depth = packet[1]
        pid, drawable, w, h = struct.unpack_from("<IIHH", packet, 4)
        self.pixmaps[pid] = {
            "id": pid, "drawable": drawable, "width": w, "height": h,
            "depth": depth,
            "root": drawable if drawable in self.windows else ROOT_WINDOW,
        }
        self._ensure_drawable(pid, w, h, depth)

    def _req_54(self, packet):                                        # FreePixmap
        pid = struct.unpack_from("<I", packet, 4)[0]
        self.pixmaps.pop(pid, None)
        self.drawables.pop(pid, None)

    def _req_55(self, packet):                                         # CreateGC
        gid, drawable = struct.unpack_from("<II", packet, 4)
        self.gcs[gid] = drawable

    def _req_60(self, packet):                                           # FreeGC
        self.gcs.pop(struct.unpack_from("<I", packet, 4)[0], None)

    def _req_62(self, packet):                                        # CopyArea
        src, dst, _gc, sx, sy, w, h, dx, dy = struct.unpack_from(
            "<IIIhhHHhh", packet, 4)
        rec = {"src": src, "dst": dst, "sx": sx, "sy": sy, "w": w, "h": h,
               "dx": dx, "dy": dy}
        self.copy_areas.append(rec)
        self._apply_copy_area(rec)

    def _req_70(self, packet):                                # PolyFillRectangle
        self.poly_fills += 1

    def _req_72(self, packet):                                          # PutImage
        fmt = packet[1]
        drawable, _gc, w, h, dx, dy = struct.unpack_from("<IIHHhh", packet, 4)
        left_pad, depth = packet[20], packet[21]
        data = packet[24:]
        colors = self._apply_put_image(drawable, w, h, dx, dy, depth, fmt, data, left_pad)
        self.put_images.append({"drawable": drawable, "w": w, "h": h, "depth": depth,
                                "format": fmt, "dx": dx, "dy": dy,
                                "nbytes": len(data), "colors": colors})

    def _req_78(self, packet):                                    # CreateColormap
        cmap, window, visual = struct.unpack_from("<III", packet, 4)
        self.colormaps[cmap] = {"window": window, "visual": visual}
        win = self.windows.get(window)
        if win is not None:
            win["colormap"] = cmap

    def _req_84(self, packet):                                        # AllocColor
        cmap, r, g, b = struct.unpack_from("<IHHH", packet, 4)
        pixel = ((r >> 8) << 16) | ((g >> 8) << 8) | (b >> 8)
        self.alloc_colors.append({"cmap": cmap, "r": r, "g": g, "b": b, "pixel": pixel})
        self._reply(struct.pack("<HHHHI", r, g, b, 0, pixel))

    def _req_85(self, packet):                                    # AllocNamedColor
        cmap = struct.unpack_from("<I", packet, 4)[0]
        n = struct.unpack_from("<H", packet, 8)[0]
        name = packet[12:12 + n].decode("latin-1")
        rgb = _named_color(name)
        pixel = ((rgb[0] >> 8) << 16) | ((rgb[1] >> 8) << 8) | (rgb[2] >> 8)
        self.alloc_colors.append({"cmap": cmap, "r": rgb[0], "g": rgb[1],
                                  "b": rgb[2], "pixel": pixel, "name": name})
        self._reply(struct.pack("<IHHHHHH", pixel, rgb[0], rgb[1], rgb[2],
                                rgb[0], rgb[1], rgb[2]) + b"\x00" * 8)

    def _req_91(self, packet):                                        # QueryColors
        # 权威线格式（xcb xproto.h xcb_query_colors_request_t）：核心请求头 4 字节
        # （opcode@0 / pad@1 / length@2 字长），随后 cmap@4、LISTofCARD32 pixels@8；
        # ncolors 字段不存在，数量由请求长度推出（实测包头 5b00 0201 20000000 …
        # → 91 / pad / 258 字长(1032B) / cmap=32 / 首像素=0，即 256 个像素起于 @8）
        n = (len(packet) - 8) // 4
        self.query_colors += 1
        out = bytearray()
        for i in range(n):
            pixel = struct.unpack_from("<I", packet, 8 + i * 4)[0]
            out += struct.pack("<HHHH", pixel & 0xFF, (pixel >> 8) & 0xFF,
                               (pixel >> 16) & 0xFF, 0)
        self._reply(struct.pack("<H", n), extra=bytes(out))

    def _req_92(self, packet):                                        # LookupColor
        n = struct.unpack_from("<H", packet, 8)[0]
        name = packet[12:12 + n].decode("latin-1")
        rgb = _named_color(name)
        self._reply(struct.pack("<HHHHHH", rgb[0], rgb[1], rgb[2],
                                rgb[0], rgb[1], rgb[2]))

    def _req_97(self, packet):                                      # QueryBestSize
        # 权威线格式（xcb xproto.h xcb_query_best_size_request_t）：drawable@4、
        # width@8、height@10（请求共 12 字节）；应答的 width/height 同样在固定区 8/10。
        w, h = struct.unpack_from("<HH", packet, 8)
        self._reply(struct.pack("<HH", w, h))

    def _req_98(self, packet):                                      # QueryExtension
        n = struct.unpack_from("<H", packet, 4)[0]
        name = packet[8:8 + n].decode("latin-1")
        if name == "SHAPE":
            self.extensions["SHAPE"] = SHAPE_MAJOR_OPCODE
            self._reply(bytes([1, SHAPE_MAJOR_OPCODE, 64, 128]))
        else:
            self._reply(bytes([0, 0, 0, 0]))

    def _req_99(self, packet):                                      # ListExtensions
        # xcb 的 xcb_get_extension_data 依此应答建表（名数 = detail 字节，
        # 名表为额外数据，各名补齐到 4 字节）；不声明则 XShapeCombineMask 直接报
        # "extension SHAPE missing"，扩展请求永不发出。
        names = b""
        for name in EXTENSION_NAMES:
            raw = name.encode("latin-1")
            names += raw + b"\x00" * (-len(raw) % 4)
        self.extension_list_served = list(EXTENSION_NAMES)
        self._reply(b"", extra=names, detail=len(EXTENSION_NAMES))

    def _req_extension(self, opcode, packet):         # 扩展请求（SHAPE 等）
        pass

    def _dispatch_extension(self, opcode, packet):
        """扩展请求入口：opcode>=128，请求字节 1 为 minor opcode。"""
        index = opcode - SHAPE_MAJOR_OPCODE
        minor = packet[1]
        if index == 0 and minor in (SHAPE_MINOR_MASK, SHAPE_MINOR_RECTANGLES,
                                    SHAPE_MINOR_COMBINE):
            # 权威线格式（xcb shape.h）：扩展头 4 字节之后依次 operation@4、
            # destination_kind@5、pad@6-7、destination_window@8、x@12、y@14、
            # source@16（Mask 为位图 / Combine 为窗口 / Rectangles 起为矩形表）
            kind = packet[5]
            dest = struct.unpack_from("<I", packet, 8)[0]
            x_off, y_off = struct.unpack_from("<hh", packet, 12)
            src = struct.unpack_from("<I", packet, 16)[0]
            self.shape_masks.append({"dest": dest, "kind": kind, "src": src,
                                     "x": x_off, "y": y_off, "minor": minor})

    # ── 属性值解析 ──
    @staticmethod
    def _parse_cw_values(mask, packet, offset):
        out = {}
        pos = offset
        for bit, key in CW_FIELDS:
            if mask & bit:
                if pos + 4 > len(packet):
                    break
                out[key] = struct.unpack_from("<I", packet, pos)[0]
                pos += 4
        return out

    def _atom_name(self, atom):
        return self.atom_names.get(atom, PREDEFINED_ATOMS.get(atom, "ATOM:%d" % atom))

    # ── 帧缓冲 ──
    def _ensure_drawable(self, did, w, h, depth):
        if depth < FB_MIN_DEPTH:
            self.drawables.setdefault(did, {"w": w, "h": h, "depth": depth, "fb": None})
            return
        self.drawables[did] = {"w": w, "h": h, "depth": depth, "fb": bytearray(w * h * 4)}

    def _apply_put_image(self, drawable, w, h, dx, dy, depth, fmt, data, left_pad):
        rec = self.drawables.get(drawable)
        if rec is None or rec["fb"] is None or depth < FB_MIN_DEPTH or fmt != 2:
            return []
        fb, stride = rec["fb"], rec["w"]
        _ = left_pad
        colors = set()
        for row in range(h):
            base = row * w * 4
            if base + w * 4 > len(data):
                break
            for col in range(w):
                px = bytes(data[base + col * 4: base + col * 4 + 4])
                colors.add(px)
                X, Y = dx + col, dy + row
                if 0 <= X < rec["w"] and 0 <= Y < rec["h"]:
                    off = (Y * stride + X) * 4
                    fb[off:off + 4] = px
        return sorted(int.from_bytes(c, "little") for c in colors)

    def _apply_copy_area(self, rec):
        src, dst = self.drawables.get(rec["src"]), self.drawables.get(rec["dst"])
        if src is None or dst is None or src["fb"] is None or dst["fb"] is None:
            return
        w, h = rec["w"], rec["h"]
        rows = []
        for row in range(h):
            sy = rec["sy"] + row
            if not (0 <= sy < src["h"]):
                rows.append(None)
                continue
            off = (sy * src["w"] + rec["sx"]) * 4
            rows.append(bytes(src["fb"][off:off + w * 4]))
        for row, data in enumerate(rows):
            if data is None:
                continue
            dy = rec["dy"] + row
            if not (0 <= dy < dst["h"]):
                continue
            off = (dy * dst["w"] + rec["dx"]) * 4
            dst["fb"][off:off + len(data)] = data

    # ── 证据查询辅助（供断言使用） ──
    def framebuffer(self, drawable_id):
        rec = self.drawables.get(drawable_id)
        return rec["fb"] if rec else None

    def window_copy_count(self, window_ids=None):
        return sum(1 for rec in self.copy_areas
                   if rec["dst"] in self.windows
                   and (window_ids is None or rec["dst"] in window_ids))

    def pixmap_copy_count(self):
        return sum(1 for rec in self.copy_areas if rec["dst"] in self.pixmaps)

    def region(self, drawable_id, x, y, w, h):
        rec = self.drawables.get(drawable_id)
        if rec is None or rec["fb"] is None:
            return None
        out = []
        for row in range(y, y + h):
            if not (0 <= row < rec["h"]):
                continue
            off = (row * rec["w"] + x) * 4
            out.append(bytes(rec["fb"][off:off + w * 4]))
        return b"".join(out)

    def distinct_colors(self, drawable_id):
        rec = self.drawables.get(drawable_id)
        if rec is None or rec["fb"] is None:
            return 0
        fb = rec["fb"]
        return len({bytes(fb[i:i + 4]) for i in range(0, len(fb), 4)})

    def draw_op_fingerprint(self, drawable_id):
        """pixmap 内部绘制算子指纹（与时钟无关的稳定证据）。"""
        ops = []
        for rec in self.copy_areas:
            if rec["src"] == drawable_id and rec["dst"] == drawable_id:
                ops.append((rec["sx"], rec["sy"], rec["w"], rec["h"]))
        return sorted(set(ops))

    # ── 终止：注入协议错误 ──
    def _maybe_finish(self):
        if self._dead or self.client_exit_reason is not None:
            return
        copies = self.window_copy_count()
        timed_out = (self.auto_stop_seconds is not None and self.started_at is not None
                     and (time.time() - self.started_at) > self.auto_stop_seconds)
        if copies < self.auto_stop_copies and not timed_out:
            return
        last = self.requests[-1] if self.requests else (0, 0, "?")
        self.inject_error(last[0], last[1],
                          "window_copies=%d timeout=%s" % (copies, timed_out))
        self.client_exit_reason = "injected_error"
        threading.Thread(target=self._close_later, daemon=True).start()

    def _close_later(self, delay=3.0):
        time.sleep(delay)
        conn = self._conn
        if conn is not None:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass

    def inject_error(self, sequence, opcode, reason=""):
        """按 X11 协议发送一个 Error（Xlib 默认错误处理器会打印并 exit(1)）。"""
        buf = bytearray(32)
        buf[0] = 0
        buf[1] = ERROR_BAD_IMPLEMENTATION
        struct.pack_into("<H", buf, 2, sequence & 0xFFFF)
        struct.pack_into("<H", buf, 8, 0)
        buf[10] = opcode & 0xFF
        self.errors.append("injected error after seq=%d opcode=%d (%s)"
                           % (sequence, opcode, reason))
        self._send(bytes(buf))

    # ── 证据汇总 ──
    def report(self):
        lines = ["headless X11 peer: DISPLAY=%s port=%d setup=%s"
                 % (self.display_string, self.port, self.setup_done)]
        if self.request_counts:
            lines.append("  请求计数: %s" % (", ".join(
                "%s=%d" % (k, v) for k, v in sorted(self.request_counts.items()))))
        for wid, win in sorted(self.windows.items(), key=lambda kv: kv[1]["order"]):
            lines.append("  window 0x%08x parent=0x%08x %dx%d depth=%d class=%d"
                         % (wid, win["parent"], win["width"], win["height"],
                            win["depth"], win["class"]))
            if "EventMask" in win["values"]:
                lines.append("    CWEventMask=0x%08x (%s)"
                             % (win["values"]["EventMask"],
                                _mask_names(win["values"]["EventMask"])))
        for pid, pix in sorted(self.pixmaps.items()):
            lines.append("  pixmap 0x%08x %dx%d depth=%d"
                         % (pid, pix["width"], pix["height"], pix["depth"]))
        for rec in self.put_images:
            lines.append("  PutImage drawable=0x%08x %dx%d depth=%d fmt=%d 颜色数=%d 前 8 色=%s"
                         % (rec["drawable"], rec["w"], rec["h"], rec["depth"],
                            rec["format"], len(rec["colors"]), rec["colors"][:8]))
        for sm in self.shape_masks:
            lines.append("  ShapeMask dest=0x%08x kind=%d src=0x%08x minor=%d"
                         % (sm["dest"], sm["kind"], sm["src"], sm["minor"]))
        lines.append("  MapWindow: %s" % (["0x%08x" % w for w in self.mapped],))
        lines.append("  CopyArea 总数=%d（→窗口 %d / →pixmap %d）"
                     % (len(self.copy_areas), self.window_copy_count(),
                        self.pixmap_copy_count()))
        for key in sorted(self.properties):
            rec = self.properties[key]
            lines.append("  property win=0x%08x %s type=%s fmt=%d n=%d %s"
                         % (key[0], key[1], rec["type"], rec["format"],
                            rec["nelements"], _property_summary(rec)))
        lines.append("  AllocColor %d 次 前 6=%s"
                     % (len(self.alloc_colors),
                        [(c["r"], c["g"], c["b"]) for c in self.alloc_colors[:6]]))
        lines.append("  QueryColors=%d SHAPE=%s 退出=%s"
                     % (self.query_colors, self.extensions, self.client_exit_reason))
        if self.errors:
            lines.append("  errors: %s" % (self.errors,))
        return "\n".join(lines)


def _mask_names(mask):
    return "|".join(name for bit, name in EVENT_MASK_NAMES if mask & bit)


def _property_summary(rec):
    fmt, raw = rec["format"], rec["raw"]
    if fmt == 8:
        return repr(raw.decode("latin-1", "replace"))
    if fmt == 32:
        n = min(rec["nelements"], len(raw) // 4)
        return str(list(struct.unpack_from("<%dI" % n, raw, 0)))
    return "<fmt=%d>" % fmt


def _named_color(name):
    base = {
        "white": (0xFFFF, 0xFFFF, 0xFFFF), "black": (0, 0, 0),
        "red": (0xFFFF, 0, 0), "green": (0, 0xFFFF, 0), "blue": (0, 0, 0xFFFF),
        "grey": (0x8080, 0x8080, 0x8080), "gray": (0x8080, 0x8080, 0x8080),
    }
    return base.get(name.lower(), (0x8000, 0x8000, 0x8000))


def _main(argv):
    display = int(argv[1]) if len(argv) > 1 else 77
    copies = int(argv[2]) if len(argv) > 2 else 8
    seconds = float(argv[3]) if len(argv) > 3 else 30.0
    srv = HeadlessXServer(display=display, auto_stop_copies=copies,
                          auto_stop_seconds=seconds)
    srv.start()
    print("DISPLAY=%s (port %d)：累积 %d 次窗口重绘后注入协议错误"
          % (srv.display_string, srv.port, copies))
    sys.stdout.flush()
    srv.wait(max_seconds=seconds + 30)
    print(srv.report())
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
