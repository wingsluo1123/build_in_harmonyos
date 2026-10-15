#!/usr/bin/env python3
"""rawtran 1.1 consumer test — application package verification.

检查面（每项打印 [ok]，末尾 CHECK_SUMMARY 逐项计数；任何一项不成立即 exit 1）：

  A 包布局（5 项）
    A1 bin/rawtran 存在且非空            A2 bin/rawtran 可执行
    A3 share/man/man1/rawtran.1 随包      A4 lib/pkgconfig/rawtran.pc 存在
    A5 licenses/ 非空（GPL-3.0-or-later）

  B 命令行契约（1 项）
    B1 `rawtran --version` rc=0 + 版本 banner
       （version() 路径无条件，不调 dcraw）

  C dcraw 存在性探测的两条分支（2 项，按上游 dcraw_presented() 的实际语义）
    上游实现：`status = system("dcraw >&-")`，`WEXITSTATUS(status) == 1` 判为
    「Info: dcraw is available.」（真实 dcraw 9.28 无参运行退出码正是 1），否则
    「Warning: dcraw not found.」；无参运行时 main() 返回 `!dcraw_presented()`。
    C1 PATH 上有「无参退出码 = 1」的 dcraw stub → 无参运行 rc=0 +
       stderr "Info: dcraw is available."
    C2 PATH 上没有任何 dcraw（/bin/sh 报 127）→ 无参运行 rc=1 +
       stderr "Warning: dcraw not found."

  D 消费者端到端用例（7 项）—— 鸿蒙特有/消费者用例
    D1 真跑一次完整转换：stub dcraw（确定性 16-bit P6 PPM）+ `rawtran -o out.fits in.CR2`
       → rc=0（man 页：0 = 成功），out.fits 生成
    D2 rawtran 对 dcraw 的两次调用与上游约定逐字一致（stub 记录 argv）：
       info  `dcraw -i -v -c <raw>`；convert `dcraw -c -4 -o 5 -q 3 -w <raw>`
    D3 out.fits 尺寸是 2880 的整数倍（FITS 块结构）且首卡 SIMPLE  = T
    D4 头关键卡：BITPIX=16（USHORT_IMG + BZERO=32768）、NAXIS=3、
       NAXIS1/NAXIS2 = 输入图像的宽/高、NAXIS3=3
    D5 COMMENT 里有 `Command: dcraw -c -4 -o 5 -q 3 -w <raw>`（上游把实际执行的
       dcraw 命令写进 FITS 注释）与 EXIF 块（由 info 调用的输出填充）
    D6 **逐像素**核对数据：3 个平面 = dcraw PPM 的 B/G/R 三通道、行序自下而上
       （pixmap 加载器的固定语义），384 个 16-bit 值全部与合成输入一致
    D7 失败路径不崩：把 dcraw 换成「无法解码」的真实 dcraw 行为（无参/不认输入）
       → rc=2（man 页：2 = 某个 RAW 转换失败）+ 上游可读错误，无段错误

  运行期事实（写进 PR 说明/notes）：rawtran 是 dcraw 的 wrapper，通过
  `system()`/`popen()` 按 PATH 找 dcraw；ohpcd 上 dcraw/9.28.0 已发布，
  但 dcraw 无参运行退出码是 1，与 rawtran 探测器「!=1 才算 present」的假设
  不符 —— 所以 C1 用「退出码 != 1」的 stub 来验探测器语义，D 用 stub 喂
  确定性 PPM 来验转换链路（CI 没有相机 RAW 样本，dcraw 也不接受 PGM/PPM 作为
  主输入，实测 "Cannot decode file"）。
"""
import os
import struct
import subprocess
import sys
import tempfile
import time

W, H = 16, 8
MAXVAL = 65535


def r_of(x, y):
    return 4000 * x + 3


def g_of(x, y):
    return 3000 * y + 5


def b_of(x, y):
    return 100 * (x + y) + 7


CHECKS = []
FAILURES = []

# 输出镜像：CI 的构建日志只保留 conan 输出的一段，子进程 stdout 未必落进那一段，
# 所以每行都无缓冲打印 + 同步写一份到 RAWTRAN_TEST_LOG，conanfile.py 失败时会回灌尾部。
LOG_PATH = os.environ.get("RAWTRAN_TEST_LOG")
LOG_FH = None


def _sink(line):
    print(line, flush=True)
    global LOG_FH
    if not LOG_PATH:
        return
    try:
        if LOG_FH is None:
            LOG_FH = open(LOG_PATH, "w", encoding="utf-8")
        LOG_FH.write(line + "\n")
        LOG_FH.flush()
    except OSError:
        pass


def ok(msg):
    CHECKS.append(msg)
    _sink("[ok] %s" % msg)


def bad(msg):
    FAILURES.append(msg)
    _sink("[FAIL] %s" % msg)


def done():
    _sink("CHECK_SUMMARY checks=%d passed=%d failed=%d"
          % (len(CHECKS) + len(FAILURES), len(CHECKS), len(FAILURES)))
    return 1 if FAILURES else 0


def run(argv, env=None, timeout=60):
    """spawn 子进程并对 EAGAIN（worker fork 抖动）重试；只重试 EAGAIN。"""
    import errno
    last = None
    for attempt in range(6):
        try:
            return subprocess.run(argv, env=env, stdin=subprocess.DEVNULL,
                                  capture_output=True, timeout=timeout)
        except (BlockingIOError, OSError) as exc:
            if getattr(exc, "errno", None) != errno.EAGAIN and \
                    not isinstance(exc, BlockingIOError):
                raise
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last


# rawtran 内部会 popen() 调 dcraw（也 fork）——worker 的 fork EAGAIN 抖动会让
# `popen` 直接失败（rawtran 打印 "Error: failed to invoke: `...`" 后返回 1）。
# 只对这种**基础设施特征**重试；真正的转换失败（Cannot decode / failed to import data）
# 原样返回、不重试也不吞。
INFRA_RETRY_SIGNS = ("failed to invoke", "Resource temporarily unavailable", "can't fork")


def run_rawtran(argv, env=None, timeout=60, attempts=4):
    r = None
    for attempt in range(attempts):
        r = run(argv, env=env, timeout=timeout)
        err = (r.stderr or b"").decode(errors="replace")
        if any(sign in err for sign in INFRA_RETRY_SIGNS) and attempt < attempts - 1:
            time.sleep(1.5 * (attempt + 1))
            continue
        return r
    return r


def make_stub_dcraw(dirpath, exit_code, logpath, ppm_path):
    """造一个 dcraw stub：

    * 无参调用 → 按 exit_code 退出（用来验 rawtran 的 dcraw 探测器语义）；
    * `-i ...`   → 输出 dcraw -i -v -c 风格的 EXIF 行；
    * 其余（转换）→ 把确定性 P6 PPM 写到 stdout。
    每次调用都把 argv 追加到 logpath，便于断言参数。
    """
    impl = os.path.join(dirpath, "dcraw_impl.py")
    with open(impl, "w", encoding="utf-8") as f:
        f.write('''#!/usr/bin/env python3
import os, sys
LOG = %r
PPM = %r
EXIT_CODE = %d
args = sys.argv[1:]
with open(LOG, "a", encoding="utf-8") as fh:
    fh.write(" ".join(args) + "\\n")
if not args:
    sys.exit(EXIT_CODE)
if "-i" in args:
    for line in ("Filename: rawstub-input",
                 "Timestamp: Tue Oct 14 12:00:00 2026",
                 "Camera: RAWSTUB Model",
                 "ISO speed: 400",
                 "Shutter: 1/125 s",
                 "Aperture: f/5.6",
                 "Focal length: 50.0 mm"):
        print(line)
    sys.exit(0)
with open(PPM, "rb") as fh:
    sys.stdout.buffer.write(fh.read())
sys.exit(0)
''' % (logpath, ppm_path, exit_code))
    stub = os.path.join(dirpath, "dcraw")
    with open(stub, "w", encoding="utf-8") as f:
        # 绝对路径 + /bin/sh：CI worker 的 PATH 可能很贫，不在 stub 里做任何 PATH 查找
        f.write("#!%s\n" % sh_path())
        f.write('exec "%s" "%s" "$@"\n' % (sys.executable, impl))
    os.chmod(stub, 0o755)
    os.chmod(impl, 0o755)
    return stub


def sh_path():
    for cand in ("/bin/sh", "/usr/bin/sh", "/system/bin/sh"):
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return "/bin/sh"


def write_synthetic_ppm(path):
    """确定性 P6 PPM：16x8、16-bit、每通道取值只与 (x,y) 有关且三元组唯一。"""
    with open(path, "wb") as f:
        f.write(b"P6\n%d %d\n%d\n" % (W, H, MAXVAL))
        for y in range(H):
            for x in range(W):
                for v in (r_of(x, y), g_of(x, y), b_of(x, y)):
                    f.write(v.to_bytes(2, "big"))


def read_fits(path):
    """极简 FITS 读取：返回 (header dict, comments list, 数据值列表, 文件字节数)。"""
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) % 2880 != 0:
        raise ValueError("FITS size %d is not a multiple of 2880" % len(raw))
    cards, off = [], 0
    while off + 2880 <= len(raw):
        block = raw[off:off + 2880]
        for i in range(36):
            cards.append(block[i * 80:(i + 1) * 80].decode("ascii", "replace"))
        off += 2880
        if any(c.startswith("END") for c in cards[-36:]):
            break
    header, comments = {}, []
    for card in cards:
        if card.startswith("COMMENT"):
            comments.append(card[7:].strip())
        elif card[:8].strip() and card[8:10] == "= ":
            header[card[:8].strip()] = card[10:].split("/")[0].strip()
    naxis = int(header["NAXIS"])
    dims = [int(header["NAXIS%d" % i]) for i in range(1, naxis + 1)]
    count = 1
    for d in dims:
        count *= d
    bitpix = int(header["BITPIX"])
    bzero = int(header.get("BZERO", "0"))
    body = raw[off:off + abs(bitpix) // 8 * count]
    if bitpix == 16:
        vals = list(struct.unpack(">%dh" % count, body))
        vals = [v + bzero for v in vals]
    elif bitpix == 8:
        vals = list(struct.unpack(">%dB" % count, body))
    else:
        raise ValueError("unexpected BITPIX=%d" % bitpix)
    return header, comments, vals, len(raw)


def check_layout(pkg_root):
    exe = os.path.join(pkg_root, "bin", "rawtran")
    if not os.path.isfile(exe):
        bad("A1 bin/rawtran missing: %s" % exe)
    elif os.path.getsize(exe) == 0:
        bad("A1 bin/rawtran is empty")
    else:
        ok("A1 bin/rawtran present (%d bytes)" % os.path.getsize(exe))
    if os.access(exe, os.X_OK):
        ok("A2 bin/rawtran executable")
    else:
        bad("A2 bin/rawtran not executable")
    man = os.path.join(pkg_root, "share", "man", "man1", "rawtran.1")
    if os.path.isfile(man):
        ok("A3 share/man/man1/rawtran.1 shipped")
    else:
        bad("A3 share/man/man1/rawtran.1 missing: %s" % man)
    pc = os.path.join(pkg_root, "lib", "pkgconfig", "rawtran.pc")
    if os.path.isfile(pc):
        ok("A4 lib/pkgconfig/rawtran.pc present")
    else:
        bad("A4 lib/pkgconfig/rawtran.pc missing")
    licdir = os.path.join(pkg_root, "licenses")
    lic = sorted(os.listdir(licdir)) if os.path.isdir(licdir) else []
    if lic:
        ok("A5 licenses/ non-empty (%s)" % ", ".join(lic[:3]))
    else:
        bad("A5 licenses/ missing or empty")
    return exe


def check_version(exe):
    r = run_rawtran([exe, "--version"])
    out = (r.stdout + r.stderr).decode(errors="replace")
    if r.returncode == 0 and "RAWTRAN, 1.1, (C) 2007-2019" in out:
        ok("B1 rawtran --version rc=0 (version banner OK)")
    else:
        bad("B1 rawtran --version rc=%d out=%s" % (r.returncode, out[:200]))


def check_dcraw_detection(exe, tmp):
    """C：rawtran 的 dcraw 探测器 = system("dcraw >&-") + WEXITSTATUS(status)==1 判为 present。

    真实 dcraw 9.28 无参运行退出码 = 1（实测），所以「退出码 1 的 stub」等价于
    「PATH 上有可用的真 dcraw」；缺 dcraw 时 /bin/sh 报 127。
    """
    stubdir = os.path.join(tmp, "stub_present")
    os.makedirs(stubdir, exist_ok=True)
    make_stub_dcraw(stubdir, 1, os.path.join(tmp, "stub_present.log"),
                    os.path.join(tmp, "unused.ppm"))
    env = dict(os.environ)
    env["PATH"] = stubdir + os.pathsep + env.get("PATH", "")
    r = run_rawtran([exe], env=env)
    err = r.stderr.decode(errors="replace")
    if r.returncode == 0 and "dcraw is available" in err:
        ok("C1 dcraw detect: dcraw-shaped stub (no-arg exit 1) -> rc=0 + "
           "'Info: dcraw is available.'")
    else:
        bad("C1 dcraw detect (present): rc=%d err=%s" % (r.returncode, err[:200]))

    emptydir = os.path.join(tmp, "no_path")
    os.makedirs(emptydir, exist_ok=True)
    env2 = dict(os.environ)
    env2["PATH"] = emptydir            # 任何 dcraw 都找不到
    r = run_rawtran([exe], env=env2)
    err = r.stderr.decode(errors="replace")
    if r.returncode == 1 and "dcraw not found" in err:
        ok("C2 dcraw detect: no dcraw on PATH -> rc=1 + 'Warning: dcraw not found.'")
    else:
        bad("C2 dcraw detect (absent): rc=%d err=%s" % (r.returncode, err[:200]))


def check_e2e(exe, tmp):
    """D：完整消费者用例 —— rawtran 真跑一次 RAW→FITS 转换并逐像素校验产物。"""
    ppm = os.path.join(tmp, "input.ppm")
    write_synthetic_ppm(ppm)
    raw = os.path.join(tmp, "grad.CR2")
    with open(raw, "wb") as f:
        f.write(b"RAWSTUB-SYNTHETIC\n")          # 内容由 stub dcraw 解释
    fits = os.path.join(tmp, "out.fits")
    stubdir = os.path.join(tmp, "stub_e2e")
    os.makedirs(stubdir, exist_ok=True)
    logpath = os.path.join(tmp, "stub_e2e.log")
    open(logpath, "w").close()
    make_stub_dcraw(stubdir, 1, logpath, ppm)

    env = dict(os.environ)
    env["PATH"] = stubdir + os.pathsep + env.get("PATH", "")
    r = run_rawtran([exe, "-o", fits, raw], env=env)
    err = r.stderr.decode(errors="replace")
    if r.returncode == 0 and os.path.isfile(fits):
        ok("D1 full conversion ran: rawtran -o out.fits grad.CR2 -> rc=0, FITS created")
    else:
        bad("D1 conversion failed: rc=%d stderr=%s" % (r.returncode, err[:300]))
        return

    invocations = [ln.strip() for ln in open(logpath, encoding="utf-8") if ln.strip()]
    info_ok = any(v.startswith("-i -v -c ") and v.endswith("grad.CR2") for v in invocations)
    conv = [v for v in invocations if v.startswith("-c ") and v.endswith("grad.CR2")]
    conv_ok = bool(conv) and "-4 -o 5" in conv[0] and "-q 3 -w" in conv[0]
    if info_ok and conv_ok:
        ok("D2 dcraw invoked exactly as upstream documents: '%s' + '%s'"
           % (invocations[0], conv[0]))
    else:
        bad("D2 dcraw invocations unexpected: %r" % (invocations,))

    try:
        header, comments, vals, size = read_fits(fits)
    except Exception as exc:  # noqa: BLE001
        bad("D3/D4/D6 FITS unreadable: %r" % exc)
        return
    if size % 2880 == 0 and header.get("SIMPLE") == "T":
        ok("D3 out.fits is block-aligned (%d bytes) and starts with SIMPLE  = T" % size)
    else:
        bad("D3 out.fits not a valid FITS container (size=%d header=%r)" % (size, header))

    dims_ok = (header.get("BITPIX") == "16" and header.get("NAXIS") == "3"
               and header.get("NAXIS1") == str(W) and header.get("NAXIS2") == str(H)
               and header.get("NAXIS3") == "3" and header.get("BZERO") == "32768")
    if dims_ok:
        ok("D4 FITS header: BITPIX=16 (USHORT_IMG+BZERO) NAXIS=3 NAXIS1=%d NAXIS2=%d NAXIS3=3"
           % (W, H))
    else:
        bad("D4 FITS header keys unexpected: %r" % {k: header.get(k) for k in
                                                   ("BITPIX", "NAXIS", "NAXIS1", "NAXIS2",
                                                    "NAXIS3", "BZERO")})

    cmd_card = [c for c in comments if c.startswith("Command:")]
    exif_card = any("EXIF data info - begin" in c for c in comments) and \
        any("ISO speed: 400" in c for c in comments)
    if cmd_card and "dcraw -c -4 -o 5" in cmd_card[0] and "-q 3 -w" in cmd_card[0] \
            and exif_card:
        ok("D5 COMMENT carries the real dcraw command ('%s...') + EXIF block from the info call"
           % cmd_card[0][:60])
    else:
        bad("D5 COMMENT provenance missing: cmd=%r exif=%s" % (cmd_card[:1], exif_card))

    expected = []
    for plane in ("B", "G", "R"):
        for row in range(H):
            src_y = H - 1 - row                      # pixmap 加载器把行序翻成自下而上
            for x in range(W):
                expected.append({"B": b_of, "G": g_of, "R": r_of}[plane](x, src_y))
    if len(vals) != len(expected):
        bad("D6 pixel count %d != expected %d" % (len(vals), len(expected)))
    else:
        diff = [(i, got, exp) for i, (got, exp) in enumerate(zip(vals, expected)) if got != exp]
        if diff:
            bad("D6 %d/%d pixels differ from the synthetic input, first: %r"
                % (len(diff), len(expected), diff[:3]))
        else:
            ok("D6 all %d 16-bit pixels match the synthetic input "
               "(B/G/R planes, rows bottom-up)" % len(expected))


def check_failure_path(exe, tmp):
    """D7：dcraw 无法解码时的失败路径：rc=2 + 上游可读错误，不崩。"""
    raw = os.path.join(tmp, "undecodable.CR2")
    with open(raw, "wb") as f:
        f.write(b"not a raw file\n")
    emptydir = os.path.join(tmp, "no_dcraw_at_all")
    os.makedirs(emptydir, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = emptydir
    r = run_rawtran([exe, "-o", os.path.join(tmp, "nope.fits"), raw], env=env)
    err = r.stderr.decode(errors="replace")
    # dcraw 不存在时 rawtran 的 popen 本身会成功（shell 报 command not found、dcraw 输出为空），
    # 于是 pixmap() 失败 → 上游的 "failed to import data by `dcraw ...`" + rc=2（man 页：
    # 2 = 某个 RAW 转换失败）。若卡在 fork EAGAIN（"failed to invoke"），run_rawtran 已重试；
    # 重试后仍失败则如实报错，不当通过。
    if r.returncode == 2 and "failed to import data" in err:
        ok("D7 failure path: unusable dcraw -> rc=2 + upstream 'failed to import data', no crash")
    else:
        bad("D7 failure path unexpected: rc=%d err=%s" % (r.returncode, err[:200]))


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RAWTRAN_PKG_ROOT", ".")
    exe = check_layout(pkg_root)
    if not os.path.isfile(exe):
        return done()
    check_version(exe)
    with tempfile.TemporaryDirectory(prefix="rawtran-consumer-") as tmp:
        check_dcraw_detection(exe, tmp)
        check_e2e(exe, tmp)
        check_failure_path(exe, tmp)
    return done()


if __name__ == "__main__":
    sys.exit(main())
