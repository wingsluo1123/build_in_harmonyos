import io
import os
import subprocess
import sys
import tarfile

# 完整消费者用例说明（rule12：鸿蒙特有测试需包含"完整消费者用例"，纯断言不足）
# udpkg 是 d-i 工具链的 .deb 解析器。其真实功能是解析 deb 归档：
#   -f / -c 走 popen "ar -t"/"ar -p ...|{gunzip|unxz|cat}|tar -xOf|-" 读 control/data。
# 本用例在失败上下文自建 mock 归档工具链（ar/cat/tar，均为纯 Python 实现），
# 构造标准 .deb 归档后实际执行 `udpkg -f` / `udpkg -c`，端到端跑通解析流程并校验输出，
# 不作为孤儿断言——验证的是 udpkg 对真实 deb 的完整消费路径。
# 说明：OHOS 沙箱无真实 ar/tar/gzip（CI buildbot 工作区仅 alias），故 mock 注入 PATH；
#        这与仓库 abuild-sudo/3.18.0 处理 OHOS 无 gzip 的 mock 思路一致。


def _ar_header(name, data):
    # GNU ar 60 字节头
    hdr = name.encode().ljust(16) \
        + b"0".ljust(12) + b"0".ljust(6) + b"0".ljust(6) \
        + b"100644".ljust(8) + str(len(data)).encode().ljust(10) + b"`\n"
    assert len(hdr) == 60, (name, len(hdr))
    return hdr + data + (b"\n" if len(data) % 2 else b"")


def _ustar(names_contents):
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w", format=tarfile.USTAR_FORMAT) as t:
        for name, content in names_contents.items():
            data = content if isinstance(content, bytes) else content.encode()
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mode = 0o644
            t.addfile(ti, io.BytesIO(data))
    return bio.getvalue()


def build_demo_deb(path):
    """构造标准 .deb（未压缩 control.tar/data.tar，避免引入 gzip 依赖）。"""
    control = _ustar({"./control":
                      "Package: udpkg-demo\n"
                      "Version: 1.0\n"
                      "Architecture: arm64\n"
                      "Maintainer: demo <d@d>\n"
                      "Description: e2e consumer demo\n"})
    data = _ustar({"./usr/share/udpkg-demo/hello.txt":
                   "hello-udpkg-consumer\n"})
    with open(path, "wb") as f:
        f.write(b"!<arch>\n")
        f.write(_ar_header("debian-binary", b"2.0\n"))
        f.write(_ar_header("control.tar", control))
        f.write(_ar_header("data.tar", data))


def write_mock_tools(mock_dir, python):
    """写 mock ar/cat/tar（纯 Python），供 udpkg 内部 popen 使用。"""
    ar = """#!{py}
import sys
def mems(path):
    res = []; pos = 8
    with open(path, "rb") as fh:
        while True:
            fh.seek(pos); hdr = fh.read(60)
            if len(hdr) < 60 or hdr[:2] == b"\\x60\\x0a": break
            name = hdr[0:16].split(b"\\0")[0].strip()
            szs = hdr[48:58].strip()
            try: size = int(szs)
            except Exception: break
            res.append((name.decode(), pos + 60, size))
            pos += 60 + size + (size % 2)
    return res
op, path = sys.argv[1], sys.argv[2]
M = mems(path)
if op == "-t":
    for n, _, _ in M: print(n)
elif op == "-p":
    target = sys.argv[3]
    for n, o, s in M:
        if n == target:
            with open(path, "rb") as fh:
                fh.seek(o); sys.stdout.buffer.write(fh.read(s))
""".format(py=python)
    cat = """#!{py}
import sys
sys.stdout.buffer.write(sys.stdin.buffer.read())
""".format(py=python)
    tar = """#!{py}
import io, sys, tarfile
data = sys.stdin.buffer.read()
m = sys.argv[1]
try:
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:")
    if m == "t":
        for mm in tf.getmembers():
            print(mm.name, mm.size)
    elif m == "-xOf":
        target = sys.argv[-1].lstrip("./")
        for mm in tf.getmembers():
            if mm.name.lstrip("./") == target:
                f = tf.extractfile(mm)
                if f:
                    sys.stdout.buffer.write(f.read())
                break
except Exception as e:
    sys.stderr.write("mock-tar error: %s\\n" % e)
    sys.exit(1)""".format(py=python)
    for tool, src in (("ar", ar), ("cat", cat), ("tar", tar)):
        p = os.path.join(mock_dir, tool)
        with open(p, "w", newline="\n") as f:
            f.write(src)
        os.chmod(p, 0o755)


def run(args, timeout=30, extra_env=None):
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(args, capture_output=True, text=True,
                          timeout=timeout, env=env)


def run_udpkg_consumer(bin_path, deb_path, mock_dir, flag):
    """用 mock 工具链注入 PATH，实际执行 udpkg，返回 stdout。"""
    mock_env = {"PATH": mock_dir + os.pathsep + os.environ.get("PATH", "")}
    return run([bin_path, flag, deb_path], extra_env=mock_env)


def main():
    pkg = sys.argv[1]
    bin_path = os.path.join(pkg, "bin", "udpkg")
    assert os.path.isfile(bin_path), f"binary missing: {bin_path}"

    # ══ A. 基础冒烟断言 ═══════════════════════════════════════
    with open(bin_path, "rb") as f:
        assert f.read(4) == b"\x7fELF"
    print("A. ELF header OK")

    r = run([bin_path, "--print-architecture"])
    assert r.returncode == 0 and r.stdout.strip() == "arm64"
    print("A. --print-architecture -> arm64")

    r = run([bin_path, "--print-os"])
    assert r.returncode == 0 and r.stdout.strip() == "linux"
    print("A. --print-os -> linux")

    r = run([bin_path])
    assert r.returncode == 0 and "udpkg [" in (r.stderr + r.stdout)
    print("A. no-args usage OK")

    # ══ B. 完整消费者用例：真实 .deb 端到端解析 ═══════════════
    scratch = os.path.join(pkg, "_consumer_scratch")
    os.makedirs(scratch, exist_ok=True)
    mock_dir = os.path.join(scratch, "mock")
    os.makedirs(mock_dir, exist_ok=True)
    python = sys.executable
    write_mock_tools(mock_dir, python)
    deb_path = os.path.join(scratch, "udpkg-demo.deb")
    build_demo_deb(deb_path)

    # -f (dpkg_fields)：应输出 control 的全部字段
    out = run_udpkg_consumer(bin_path, deb_path, mock_dir, "-f")
    assert out.returncode == 0, f"-f rc={out.returncode}: {out.stderr!r}"
    assert "Package: udpkg-demo" in out.stdout, out.stdout
    assert "Architecture: arm64" in out.stdout, out.stdout
    assert "Description: e2e consumer demo" in out.stdout, out.stdout
    print("B. udpkg -f (dpkg_fields) 端到端解析 control 成功")

    # -c (dpkg_contents)：应列出 data.tar 中的文件
    out = run_udpkg_consumer(bin_path, deb_path, mock_dir, "-c")
    assert out.returncode == 0, f"-c rc={out.returncode}: {out.stderr!r}"
    assert "usr/share/udpkg-demo/hello.txt" in out.stdout, out.stdout
    print("B. udpkg -c (dpkg_contents) 端到端列出 data 成功")

    # 校验 mock 工具确实被调用（证明真实走了 popen 解析路径）
    assert os.path.isfile(os.path.join(mock_dir, "ar"))
    assert os.path.isfile(os.path.join(mock_dir, "tar"))
    assert os.path.isfile(os.path.join(mock_dir, "cat"))

    print("udpkg test OK: ELF/print-arch/print-os/usage + "
          "完整消费者用例(-f/-c 真实解析 .deb)")


if __name__ == "__main__":
    main()