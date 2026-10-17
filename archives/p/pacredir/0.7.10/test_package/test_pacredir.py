#!/usr/bin/env python3
"""pacredir/0.7.10 消费者测试驱动（16 个独立检查项）。

口径：**独立检查项数量**。上游 pacredir 0.7.10 没有任何测试资产（无 tests/
目录，Makefile 无 check/test 目标，tarball 内 0 个测试文件），因此下列 16 项
全部是本次适配新增；其中 7 项是 HarmonyOS 平台特有测试（带 [OHOS] 标记：
3、5、6、7、11、15、16），与 MANIFEST.yml 的 harmonyos_specific_tests 一致。

只用 Python 标准库：CI worker 上没有 curl（仓内既有记录：smalt 的预下载兜底
就因 `[Errno 2] No such file or directory: 'curl'` 失效），HTTP 走 http.client，
ELF 检视走 struct 手解，均不依赖 readelf/objdump 是否在 PATH 上。

用法：test_pacredir.py <pacredir 包目录> <守护进程日志路径>
退出码：0 = 全部通过；1 = 有检查项失败。
"""
import http.client
import os
import signal
import socket
import struct
import subprocess
import sys
import time
import zlib

# 上游 config.def.h 里写死的监听端口（不可通过命令行或配置改）。
PORT = 7077
HOST = "127.0.0.1"
# 本配方从 Conan settings 编入的身份字面量（替代上游对 /etc/os-release 与
# /etc/makepkg.conf 的 $(shell) 探测）。
EXPECT_ID = "ohos"
EXPECT_ARCH = "aarch64"
EXPECT_VERSION = "0.7.10"
# 上游 style.css 原文长度（tarball 内的固定字节数，非再生成产物）。
STYLE_CSS_SIZE = 858

_results = []


def check(name, ok, detail=""):
    # detail 必须是字符串：它会被拼进 TAP 行的注释位，传非字符串会 TypeError。
    if not isinstance(detail, str):
        detail = repr(detail)
    _results.append((name, bool(ok), detail))
    print("%s - %s%s" % ("ok" if ok else "not ok", name,
                         ("  # " + detail) if detail else ""), flush=True)
    return bool(ok)


# ───────────────────────── ELF64 检视（纯 struct，不依赖 readelf）─────────────────────────
PT_LOAD, PT_GNU_STACK, PT_GNU_RELRO, PT_DYNAMIC = 1, 0x6474E551, 0x6474E552, 2
DT_NULL, DT_NEEDED, DT_STRTAB, DT_FLAGS, DT_FLAGS_1 = 0, 1, 5, 30, 0x6FFFFFFB
DF_BIND_NOW, DF_1_PIE, DF_1_NOW = 0x8, 0x08000000, 0x1
EM_AARCH64 = 183
ET_DYN = 3


class Elf64(object):
    """最小 ELF64 小端读取器：够用来断言 ABI 与加固契约。"""

    def __init__(self, path):
        self.data = open(path, "rb").read()
        if self.data[:4] != b"\x7fELF":
            raise AssertionError("%s 不是 ELF 文件" % path)
        if self.data[4] != 2:
            raise AssertionError("只支持 ELF64（实得 class=%d）" % self.data[4])
        if self.data[5] != 1:
            raise AssertionError("只支持小端 ELF（实得 data=%d）" % self.data[5])
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", self.data, 16)
        (self.e_phoff, self.e_shoff) = struct.unpack_from("<QQ", self.data, 32)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from("<HH", self.data, 54)
        self.phdrs = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            p_type, p_flags = struct.unpack_from("<II", self.data, off)
            p_offset, p_vaddr, _p_paddr, _p_filesz, _p_memsz, _p_align = \
                struct.unpack_from("<QQQQQQ", self.data, off + 8)
            self.phdrs.append((p_type, p_flags, p_offset, p_vaddr, _p_filesz))

    def has_segment(self, p_type):
        return any(p[0] == p_type for p in self.phdrs)

    def stack_flags(self):
        for p in self.phdrs:
            if p[0] == PT_GNU_STACK:
                return p[1]
        return None

    def _vaddr_to_off(self, vaddr):
        for p_type, _f, p_offset, p_vaddr, p_filesz in self.phdrs:
            if p_type == PT_LOAD and p_vaddr <= vaddr < p_vaddr + p_filesz:
                return p_offset + (vaddr - p_vaddr)
        raise AssertionError("vaddr 0x%x 不在任何 PT_LOAD 内" % vaddr)

    def _cstr(self, off):
        end = self.data.index(b"\x00", off)
        return self.data[off:end].decode("utf-8", "replace")

    def dynamic(self):
        """返回 (needed 列表, DT_FLAGS, DT_FLAGS_1)。"""
        dyn = [p for p in self.phdrs if p[0] == PT_DYNAMIC]
        if not dyn:
            return [], 0, 0
        # phdrs 元组形状: (p_type, p_flags, p_offset, p_vaddr, p_filesz)
        _p_type, _p_flags, p_offset, _p_vaddr, p_filesz = dyn[0]
        ents, strtab_vaddr = [], 0
        for i in range(p_filesz // 16):
            tag, val = struct.unpack_from("<QQ", self.data, p_offset + i * 16)
            if tag == DT_NULL:
                break
            ents.append((tag, val))
            if tag == DT_STRTAB:
                strtab_vaddr = val
        base = self._vaddr_to_off(strtab_vaddr)
        needed = [self._cstr(base + v) for t, v in ents if t == DT_NEEDED]
        flags = next((v for t, v in ents if t == DT_FLAGS), 0)
        flags1 = next((v for t, v in ents if t == DT_FLAGS_1), 0)
        return needed, flags, flags1


# ───────────────────────── PNG 校验（复刻配方里的资产链自校验）─────────────────────────
def png_inspect(blob):
    """返回 (width, height, nchunks, crc_ok, idat_rows)。CRC 逐块校验。"""
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("响应体不是 PNG（前 8 字节 %r）" % blob[:8])
    pos, chunks, crc_ok = 8, [], True
    while pos < len(blob):
        (length,) = struct.unpack(">I", blob[pos:pos + 4])
        ctype = blob[pos + 4:pos + 8]
        payload = blob[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", blob[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(ctype + payload) & 0xFFFFFFFF != crc:
            crc_ok = False
        chunks.append((ctype, payload))
        pos += 12 + length
    first = dict(chunks)
    w, h, depth, ctype_i = struct.unpack(">IIBB", first[b"IHDR"][:10])
    idat = b"".join(p for c, p in chunks if c == b"IDAT")
    raw = zlib.decompress(idat)
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype_i] * depth // 8
    rows = len(raw) // (1 + w * bpp) if (1 + w * bpp) else 0
    return w, h, len(chunks), crc_ok, rows


def sha1_hex(blob):
    import hashlib
    return hashlib.sha1(blob).hexdigest()


# ───────────────────────── HTTP ─────────────────────────
def http_get(path, timeout=10):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        # 头按小写键归一；同名多值（libmicrohttpd 可能自带一份 Server）保留成
        # 列表，免得 dict() 折叠后只剩最后一个而误判。
        multi = {}
        for k, v in resp.getheaders():
            multi.setdefault(k.lower(), []).append(v)
        single = dict((k, v[-1]) for k, v in multi.items())
        return resp.status, single, body, multi
    finally:
        conn.close()


def wait_port(timeout=25):
    """轮询直到 7077 可连；返回 True/False。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with socket.create_connection((HOST, PORT), timeout=2):
                return True
        except OSError:
            time.sleep(0.3)
    return False


proc = None


def run_cli(args, timeout=30):
    env = dict(os.environ)
    # 决定性：NOTIFY_SOCKET 存在会让 sd_notify 返回 >0，从而切到 journald-only
    # 日志路径；本测试要验的正是 OHOS 上唯一可能的那条（无 systemd）路径。
    env.pop("NOTIFY_SOCKET", None)
    env.pop("XDG_RUNTIME_DIR", None)
    r = subprocess.run([BIN] + args, capture_output=True, text=True,
                       timeout=timeout, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def static_checks():
    """检查项 1-7：CLI 身份 + ELF/ABI 契约（不需要执行守护进程）。"""
    # 1
    rc, out = run_cli(["-V"])
    check("1 -V 退出码为 0", rc == 0, "rc=%d" % rc)
    # 2
    banner = out.strip().splitlines()[-1] if out.strip() else "<空输出>"
    check("2 -V 输出含 'pacredir v%s'（VERSION 正确编入，非空）" % EXPECT_VERSION,
          ("pacredir v" + EXPECT_VERSION) in out,
          "rc=%d last_line=%r" % (rc, banner))
    # 3 [OHOS]
    ident = "%s/%s" % (EXPECT_ID, EXPECT_ARCH)
    check("3 [OHOS] -V 输出含 '%s'（ID/ARCH 由 Conan settings 编入，"
          "替代上游对 /etc/os-release 与 /etc/makepkg.conf 的 Arch 专有探测）" % ident,
          ident in out, "output=%r" % out.strip()[:160])
    # 4
    rc_h, out_h = run_cli(["-h"])
    check("4 -h 退出码为 0 且打印 usage", rc_h == 0 and "usage:" in out_h,
          "rc=%d out=%r" % (rc_h, out_h.strip()[:120]))
    # 5-7 [OHOS] ELF 契约
    elf = Elf64(BIN)
    needed, flags, flags1 = elf.dynamic()
    is_pie = elf.e_type == ET_DYN and bool(flags1 & DF_1_PIE)
    check("5 [OHOS] 产物是 ELF64 AArch64 PIE（ET_DYN + DF_1_PIE）",
          elf.e_machine == EM_AARCH64 and is_pie,
          "machine=%d type=%d flags1=0x%x" % (elf.e_machine, elf.e_type, flags1))
    bind_now = bool(flags & DF_BIND_NOW) or bool(flags1 & DF_1_NOW)
    sf = elf.stack_flags()
    nx_ok = sf is not None and not (sf & 0x1)  # PF_X == 1
    check("6 [OHOS] 加固三件套：PT_GNU_RELRO + BIND_NOW + 不可执行栈(NX)",
          elf.has_segment(PT_GNU_RELRO) and bind_now and nx_ok,
          "relro=%s bind_now=%s stack_flags=%s" % (elf.has_segment(PT_GNU_RELRO),
                                                   bind_now, sf))
    # 期望集与配方 conanfile.py「依赖图处置 4」一一对应：
    #   libcurl.so       —— 用 libcurl/8.5.0 已发布的**动态**二进制（其 SONAME 就是
    #                       无版本号的 libcurl.so，llvm-readelf -d 实测确认）。之所以
    #                       不强制 shared=False 走静态：反向方案在远程 CI #93768 上
    #                       实测失败 —— libcurl 从源码构建时 CMake 走 make -j20，撞
    #                       OHOS SELinux 禁 FIFO（E525：GNU make 的 jobserver 靠 FIFO
    #                       传并行令牌），报 jobserver mkfifo: Operation not permitted
    #                       → /bin/sh: can't fork → Error 127。那个 -j20 出自 libcurl
    #                       自己的配方，下游无从干预。
    #   libsystemd.so.0  —— systemd/261.1 的唯一动态产物（sd-bus/sd-daemon/sd-journal）。
    #   libc.so          —— OHOS musl。
    # libmicrohttpd 与 iniparser 在制品仓里本就是静态库（libmicrohttpd.a /
    # libiniparser.a），zlib/1.3.1.1 亦为静态，三者都被静态吸收、不出现在 DT_NEEDED
    # 里（R26：不往设备 /lib 塞系统同名 .so）。--as-needed 另丢掉 systemd 的 cpp_info
    # 广告、但 libsystemd.so 实际并不需要的 libzstd/liblzma。
    expect_needed = {"libcurl.so", "libsystemd.so.0", "libc.so"}
    check("7 [OHOS] DT_NEEDED 恰为 {libcurl.so, libsystemd.so.0, libc.so}"
          "（libmicrohttpd/iniparser/zlib 已静态吸收，符合 R26；libcurl 沿用已发布"
          "动态二进制以避开 E525 的 make -j FIFO 限制；--as-needed 丢掉 libsystemd.so "
          "并不需要的 libzstd/liblzma）",
          set(needed) == expect_needed, "needed=%s" % needed)


REMAINING = [
    "9 GET / 状态页",
    "10 Server 响应头身份",
    "11 [OHOS] GET /favicon.png 资产链",
    "12 GET /style.css",
    "13 GET /check 监控端点",
    "14 无 peer 时 GET /no-such-file 返回 404",
    "15 [OHOS] 首轮 mDNS 更新后进程存活",
    "16 [OHOS] SIGUSR1 状态转储",
]


def daemon_checks(log_path):
    """检查项 8-16：守护进程端到端 + 无 systemd 平台上的降级与生命周期。"""
    global proc
    # 端口占用会导致 MHD_start_daemon 失败并 exit 1，先探一次给出明确诊断。
    try:
        with socket.create_connection((HOST, PORT), timeout=2):
            check("8 守护进程在 %s:%d 上可连" % (HOST, PORT), False,
                  "端口 %d 在启动前已被占用，无法测试" % PORT)
            for name in REMAINING:
                check(name, False, "守护进程未能启动，本项无法执行")
            return
    except OSError:
        pass

    env = dict(os.environ)
    env.pop("NOTIFY_SOCKET", None)
    env.pop("XDG_RUNTIME_DIR", None)
    logf = open(log_path, "wb")
    proc = subprocess.Popen([BIN, "-v"], stdout=logf, stderr=subprocess.STDOUT,
                            env=env)
    up = wait_port()
    check("8 守护进程在 %s:%d 上可连" % (HOST, PORT), up,
          "" if up else "进程退出码=%s，日志见 %s" % (proc.poll(), log_path))
    if not up:
        logf.close()
        for name in REMAINING:
            check(name, False, "守护进程未能启动，本项无法执行")
        return

    # 9 状态页
    st, hdr, body, multi = http_get("/")
    text = body.decode("utf-8", "replace")
    ok9 = (st == 200 and hdr.get("content-type") == "text/html"
           and "pacredir status" in text
           and "<b>%s</b>" % EXPECT_ID in text
           and "<b>%s</b>" % EXPECT_ARCH in text)
    check("9 GET / 返回 200 text/html，状态页含 'pacredir status' 且渲染出编入的 "
          "Distribution=%s / Architecture=%s" % (EXPECT_ID, EXPECT_ARCH),
          ok9, "status=%d ctype=%r id_in=%s arch_in=%s"
          % (st, hdr.get("content-type"), "<b>%s</b>" % EXPECT_ID in text,
             "<b>%s</b>" % EXPECT_ARCH in text))

    # 10 Server 头也带同一份身份（ahc_echo 对每个响应都加这一条）
    want_srv = "pacredir v%s %s/%s" % (EXPECT_VERSION, EXPECT_ID, EXPECT_ARCH)
    got_srv = multi.get("server", [])
    check("10 响应的 Server 头为 '%s'" % want_srv, want_srv in got_srv,
          "server=%r" % got_srv)

    # 11 [OHOS] favicon —— 替代 resvg|oxipng 的资产链
    st, hdr, body, multi = http_get("/favicon.png")
    ok_ct = st == 200 and hdr.get("content-type") == "image/png"
    ok_etag = hdr.get("etag") == sha1_hex(body)
    detail = "status=%d ctype=%r etag_match=%s" % (st, hdr.get("content-type"), ok_etag)
    ok_png = False
    if ok_ct and ok_etag:
        try:
            w, h, nch, crc_ok, rows = png_inspect(body)
            ok_png = (w, h) == (32, 32) and crc_ok and rows == 32
            detail += " dims=%dx%d chunks=%d crc_ok=%s idat_rows=%d size=%d" % (
                w, h, nch, crc_ok, rows, len(body))
        except Exception as exc:  # noqa: BLE001 - 测试里要把异常变成失败详情
            detail += " png_error=%s" % exc
    check("11 [OHOS] GET /favicon.png 返回 200 image/png，ETag==sha1(body)，"
          "且 body 是可解码的 32x32 PNG（逐块 CRC 通过、IDAT 行数=32）——"
          "验证替代 resvg|oxipng 的纯标准库资产链端到端正确",
          ok_ct and ok_etag and ok_png, detail)

    # 12 style.css
    st, hdr, body, multi = http_get("/style.css")
    ok12 = (st == 200 and hdr.get("content-type") == "text/css"
            and len(body) == STYLE_CSS_SIZE
            and hdr.get("etag") == sha1_hex(body)
            and body.startswith(b"/* style sheet for pacredir */")
            and b"tr.offline {" in body)
    check("12 GET /style.css 返回 200 text/css，长度=%d、ETag==sha1(body)、"
          "首行与 tr.offline 规则与上游原文一致" % STYLE_CSS_SIZE,
          ok12, "status=%d ctype=%r size=%d etag_match=%s"
          % (st, hdr.get("content-type"), len(body),
             hdr.get("etag") == sha1_hex(body)))

    # 13 /check 监控端点
    st, hdr, body, multi = http_get("/check")
    check("13 GET /check 返回 200 且 body 为 'OK'（上游的监控探针端点）",
          st == 200 and body == b"OK", "status=%d body=%r" % (st, body[:32]))

    # 14 404 路径（无 peer 时 find_best_redirect 返回 NULL）
    st, hdr, body, multi = http_get("/no-such-file")
    check("14 无 peer 时 GET /no-such-file 返回 404（find_best_redirect 在空 "
          "hosts 链表上快速返回 NULL，不阻塞、不崩溃）",
          st == 404, "status=%d" % st)

    # 15 [OHOS] 首轮 update_hosts() 之后进程仍存活
    # 主循环第一次 sleep(0) 返回 0，条件 `sleepsec > 0 && update == 0` 不成立，
    # 因此启动后立即执行 update_interfaces()+update_hosts()。OHOS 上没有
    # systemd-resolved、也没有系统总线，sd_bus_open_system() 失败后上游走
    # `goto fast_finish` 优雅降级——这一项就是实测这条降级路径不 abort。
    time.sleep(3)
    alive = proc.poll() is None
    st2 = None
    if alive:
        try:
            st2 = http_get("/")[0]
        except OSError as exc:
            st2 = "http error: %s" % exc
    check("15 [OHOS] 首轮 mDNS 更新周期（无 systemd-resolved / 无系统总线）之后"
          "进程仍存活且 / 仍返回 200 —— sd_bus_open_system() 失败路径优雅降级",
          alive and st2 == 200, "alive=%s poll=%s status=%r" % (alive, proc.poll(), st2))

    # 16 [OHOS] SIGUSR1 状态转储：无 mDNS peer ⇒ Known hosts 为空
    proc.send_signal(signal.SIGUSR1)
    time.sleep(2)
    logf.flush()
    log = open(log_path, "rb").read().decode("utf-8", "replace")
    ok16 = ("Known hosts:" in log and " (none)" in log
            and "Ignored interfaces:" in log)
    check("16 [OHOS] SIGUSR1 触发状态转储且 'Known hosts:' 为 ' (none)'"
          "（无 systemd-resolved ⇒ 无 mDNS peer；同时证明非 systemd 日志回退路径"
          "在工作——OHOS 无 journald，sd_notify 返回 0 使 systemd=0）",
          ok16, "known_hosts=%s none=%s banner=%s"
          % ("Known hosts:" in log, " (none)" in log,
             ("pacredir v" + EXPECT_VERSION) in log))

    # 收尾：SIGTERM 干净退出（不计入检查项，属测试卫生）
    proc.send_signal(signal.SIGTERM)
    try:
        rc = proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        rc = "timeout"
    log = open(log_path, "rb").read().decode("utf-8", "replace")
    print("# SIGTERM 退出码=%s，日志含退出信号行=%s"
          % (rc, "quitting." in log), flush=True)
    logf.close()


def main():
    global BIN
    if len(sys.argv) != 3:
        print("usage: test_pacredir.py <package_folder> <daemon_log_path>",
              file=sys.stderr)
        return 2
    pkg, log_path = sys.argv[1], sys.argv[2]
    BIN = os.path.join(pkg, "bin", "pacredir")
    if not os.path.isfile(BIN):
        print("not ok - 找不到被测二进制 %s" % BIN)
        return 1
    print("# 被测二进制: %s (%d bytes)" % (BIN, os.path.getsize(BIN)), flush=True)
    static_checks()
    # 日志写在调用方给的路径（conan 的 test_package 构建目录）——OHOS 的 /tmp
    # 只读（E002），不能自己挑临时目录。
    try:
        daemon_checks(log_path)
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
    total = len(_results)
    failed = [n for n, ok, _ in _results if not ok]
    print("# 检查项合计: %d，失败: %d" % (total, len(failed)), flush=True)
    print("1..%d" % total, flush=True)
    if failed:
        for n in failed:
            print("# FAILED: %s" % n, flush=True)
        return 1
    print("# PACREDIR_TEST_PACKAGE_RESULT=%d/%d" % (total, total), flush=True)
    return 0


BIN = None
if __name__ == "__main__":
    sys.exit(main())
