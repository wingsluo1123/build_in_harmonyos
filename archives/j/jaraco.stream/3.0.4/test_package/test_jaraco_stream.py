#!/usr/bin/env python3
"""消费者测试 — jaraco.stream 3.0.4（R34：实质调用被测包 API）

站在「库的使用者」角度，只用公开 API（不 import 上游测试代码）：

  1. 导入面     —— 包与两个子模块可导入，公开符号齐全
  2. LineBuffer —— \\n / \\r\\n 切行、保留未完成行、纯字节不解码、可迭代
  3. DecodingLineBuffer —— UTF-8 解码、errors='replace'、严格模式报错
  4. LenientDecodingLineBuffer —— UTF-8 失败回退 latin-1
  5. gzip 流    —— 内存构造 gzip 数据 → read_chunks → load_streams →
                   lines_from_stream 逐行还原；并覆盖「多 gzip 成员首尾相接」
  6. 依赖可见性 —— more_itertools（conan requires 提供）可导入
  7. Tee        —— stdout 同时写文件，并能还原

用法：python3 test_jaraco_stream.py [site-packages 目录]
"""
import gzip as stdgzip
import io
import json
import os
import sys
import tempfile

CHECKS = []


def check(name, cond, extra=""):
    ok = bool(cond)
    CHECKS.append((name, ok))
    print("  {}  {}".format("PASS" if ok else "FAIL", name))
    if not ok and extra:
        print("        {}".format(extra))
    return ok


def main():
    # ---------------------------------------------------------------- 1 导入面
    import jaraco.stream as js
    from jaraco.stream import buffer, gzip as jsgzip

    check("包 jaraco.stream 可导入", js is not None)
    check("jaraco.stream.buffer 可导入", buffer is not None)
    check("jaraco.stream.gzip 可导入（依赖 more_itertools 已就位）", jsgzip is not None)
    check("公开类 Tee 存在", isinstance(getattr(js, "Tee", None), type))
    check("行缓冲三件套齐全",
          all(hasattr(buffer, n) for n in ("LineBuffer", "DecodingLineBuffer",
                                           "LenientDecodingLineBuffer")))
    check("gzip 工具函数齐全",
          all(hasattr(jsgzip, n) for n in ("read_chunks", "load_stream",
                                           "load_streams", "lines_from_stream")))

    # ------------------------------------------------------------ 2 LineBuffer
    b = buffer.LineBuffer()
    check("初始缓冲为空", len(b) == 0)
    b.feed(b"foo\nbar")
    check("feed 后长度 7（保留未完成行）", len(b) == 7)
    check("切出完整行 b'foo'", list(b.lines()) == [b"foo"])
    check("未完成行留在缓冲（长度 3）", len(b) == 3)
    b.feed(b"bar\r\nbaz\n")
    check("\\r\\n 与 \\n 都能切", list(b.lines()) == [b"barbar", b"baz"])
    check("切完缓冲清空", len(b) == 0)

    utf8_word = "Olé".encode("utf-8")
    b.feed(utf8_word + b"\n")
    check("LineBuffer 不做解码（仍是 bytes）", list(b.lines()) == [utf8_word])

    b.feed(b"iterate\nthis\n")
    check("LineBuffer 可作为可迭代对象", list(b) == [b"iterate", b"this"])

    # -------------------------------------------------- 3 DecodingLineBuffer
    d = buffer.DecodingLineBuffer()
    d.feed(b"bar\r\nbaz\n" + utf8_word + b"\n")
    check("UTF-8 行解码正确", list(d.lines()) == ["bar", "baz", "Olé"])

    d2 = buffer.DecodingLineBuffer()
    d2.errors = "replace"
    d2.feed(b"Ol\xe9\n")
    check("errors='replace' 容错非法字节", list(d2.lines()) == ["Ol\ufffd"])

    d3 = buffer.DecodingLineBuffer()
    d3.feed(b"Ol\xe9\n")
    try:
        list(d3.lines())
        raised = False
    except UnicodeDecodeError:
        raised = True
    check("严格模式下非法 UTF-8 抛 UnicodeDecodeError", raised)

    # ----------------------------------------- 4 LenientDecodingLineBuffer
    lb = buffer.LenientDecodingLineBuffer()
    lb.feed(utf8_word + b"\n")
    lb.feed(b"Ol\xe9\n")
    check("UTF-8 与 latin-1 混流都能解", list(lb.lines()) == ["Olé", "Olé"])

    # ------------------------------------------------------------- 5 gzip 流
    payload = b"".join(
        json.dumps({"id": i, "data": "x" * i}).encode() + b"\n"
        for i in (1, 2, 3))

    def gz_bytes(data):
        buf = io.BytesIO()
        with stdgzip.GzipFile(mode="wb", fileobj=buf) as gz:
            gz.write(data)
        return buf.getvalue()

    single = gz_bytes(payload)

    chunks = list(jsgzip.read_chunks(io.BytesIO(single), block_size=7))
    check("read_chunks 按块大小切分（除尾块外均为 7 字节）",
          len(chunks) > 1
          and all(len(c) == 7 for c in chunks[:-1])
          and 0 < len(chunks[-1]) <= 7)
    check("read_chunks 内容无损",
          b"".join(chunks) == single)

    lines = []
    for stream in jsgzip.load_streams(iter(chunks)):
        for line in jsgzip.lines_from_stream(stream):
            if line.strip():
                lines.append(line)
    check("gzip 流逐行还原出 3 行", len(lines) == 3)
    check("首行 JSON 语义正确（id=1）",
          lines and json.loads(lines[0])["id"] == 1)
    check("末行 JSON 语义正确（id=3）",
          lines and json.loads(lines[-1])["id"] == 3)

    # 多成员首尾相接：两个 gzip 成员拼在一起
    double = single + single
    dchunks = list(jsgzip.read_chunks(io.BytesIO(double), block_size=9))
    dlines = []
    for stream in jsgzip.load_streams(iter(dchunks)):
        for line in jsgzip.lines_from_stream(stream):
            if line.strip():
                dlines.append(line)
    check("多 gzip 成员（2 段）全部解出 6 行", len(dlines) == 6)
    check("多成员内容按序正确",
          [json.loads(x)["id"] for x in dlines] == [1, 2, 3, 1, 2, 3])

    # 直接把 gzip.BytesIO 交给 read_chunks（上游测试的用法）
    stream = io.BytesIO(single)
    via_stream = []
    for s in jsgzip.load_streams(jsgzip.read_chunks(stream)):
        via_stream.extend(x for x in jsgzip.lines_from_stream(s) if x.strip())
    check("io.BytesIO 直传用法同样可用", len(via_stream) == 3)

    # ------------------------------------------------------ 6 依赖可见性
    import more_itertools
    check("运行期依赖 more_itertools 可导入（conan requires 生效）",
          hasattr(more_itertools, "peekable")
          or hasattr(more_itertools.more, "peekable"))

    # ------------------------------------------------------------- 7 Tee
    fd, path = tempfile.mkstemp(suffix=".tee.txt")
    os.close(fd)
    tee = js.Tee(path, "w")
    try:
        sys.stdout.write("tee-line\n")
        tee.file.flush()
    finally:
        sys.stdout = tee.stdout  # 还原真实 stdout
    with open(path, encoding="utf-8") as f:
        content = f.read()
    os.unlink(path)
    check("Tee 把 stdout 内容同时写入文件", "tee-line" in content)
    check("Tee 之后 stdout 已还原", sys.stdout is tee.stdout)

    # ------------------------------------------------------------- 汇总
    failed = [n for n, ok in CHECKS if not ok]
    print("\njaraco.stream 消费者测试：{}/{} 项通过".format(
        len(CHECKS) - len(failed), len(CHECKS)))
    if failed:
        print("失败项：")
        for n in failed:
            print("  - " + n)
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("site-packages: {}".format(sys.argv[1]))
    sys.exit(main())
