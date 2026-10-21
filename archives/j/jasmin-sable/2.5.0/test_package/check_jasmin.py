#!/usr/bin/env python3
"""Consumer checks for the jasmin-sable package.

usage: check_jasmin.py <package-folder>

Checks（全部针对打包后的产物；分类口径：**只有具名环境信号才允许 SKIP**）：
  1. 产物齐备：`bin/jasmin`（包装脚本，可执行）、`libexec/jasmin-sable-2.5.0.jar`、
     `libexec/java-cup-11b-20160615-3.jar`（**运行期依赖，必须随包提供**）；
  2. `jasmin-sable-2.5.0.jar` 内含 `jasmin/Main.class`（主类）与 `jas/` 包（jas 库被一并编译进来）；
  3. **端到端真跑**：写一段真实的 Jasmin 汇编（打印一行字符串），用 `bin/jasmin` 汇编出 `.class`，
     再用 `java` 执行它并断言输出 —— 这一步同时验证了"包装脚本能找到两个 jar""java-cup 运行期可用"
     与"汇编器真的能工作"；
  4. 证据：两个 jar 的大小与 sha256、所用 JDK。
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile

JAR = os.path.join("libexec", "jasmin-sable-2.5.0.jar")
CUP = os.path.join("libexec", "java-cup-11b-20160615-3.jar")
LAUNCHER = os.path.join("bin", "jasmin")
ASM = r"""
.class public Hello
.super java/lang/Object
.method public static main([Ljava/lang/String;)V
    .limit stack 2
    .limit locals 1
    getstatic java/lang/System/out Ljava/io/PrintStream;
    ldc "JASMIN_OK"
    invokevirtual java/io/PrintStream/println(Ljava/lang/String;)V
    return
.end method
"""

fails = []
skips = []


def fail(msg):
    fails.append(msg)
    print("[FAIL] %s" % msg)


def ok(msg):
    print("[ok]   %s" % msg)


def skip(msg):
    skips.append(msg)
    print("[skip] %s" % msg)


def _java_home():
    for cand in (os.environ.get("JAVA_HOME", ""),
                 os.path.expanduser("~/bishengjdk17"),
                 os.path.expanduser("~/usr/local/bishengjdk17")):
        if cand and os.path.isfile(os.path.join(cand, "bin", "java")):
            return cand
    java = shutil.which("java")
    if java:
        return os.path.dirname(os.path.dirname(os.path.realpath(java)))
    return None


def check_artifacts(pkg):
    bad = []
    for rel, need_x in ((LAUNCHER, True), (JAR, False), (CUP, False)):
        path = os.path.join(pkg, rel)
        if not os.path.isfile(path):
            bad.append("%s(缺失)" % rel)
            continue
        if os.path.getsize(path) == 0:
            bad.append("%s(为空)" % rel)
        elif need_x and not os.access(path, os.X_OK):
            bad.append("%s(不可执行)" % rel)
    if bad:
        fail("产物不合格：%s" % ", ".join(bad))
        return False
    ok("产物齐备：bin/jasmin（可执行）+ libexec/ 下 jasmin jar 与 java-cup jar（运行期依赖随包提供）")
    return True


def check_jar_layout(pkg):
    path = os.path.join(pkg, JAR)
    if not os.path.isfile(path):
        return
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        fail("jasmin jar 不是合法 zip")
        return
    need = ("jasmin/Main.class", "jasmin/parser.class", "jas/ClassEnv.class")
    missing = [n for n in need if n not in names]
    if missing:
        fail("jasmin jar 缺少类：%s" % ", ".join(missing))
        return
    ok("jasmin jar 内含主类与 jas 包（jasmin/Main.class、jasmin/parser.class、jas/ClassEnv.class）")


def check_end_to_end(pkg):
    java_home = _java_home()
    if java_home is None:
        skip("具名环境信号：宿主找不到 JDK（java），无法做端到端校验")
        return
    launcher = os.path.join(pkg, LAUNCHER)
    if not os.path.isfile(launcher):
        return
    work = os.path.join(os.path.dirname(os.path.abspath(pkg.rstrip(os.sep))), "jasmin-e2e")
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)
    src = os.path.join(work, "Hello.jas")
    with open(src, "w") as fh:
        fh.write(ASM)

    env = dict(os.environ)
    env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")
    proc = subprocess.run([launcher, "Hello.jas"], cwd=work, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0:
        with open(os.path.join(pkg, JAR).replace(".jar", ".jar"), "rb") as _fh:
            pass
        fail("`jasmin Hello.jas` 执行失败（exit=%s）：%s" % (proc.returncode, out.strip()[:300]))
        return
    cls = os.path.join(work, "Hello.class")
    if not os.path.isfile(cls):
        fail("汇编未产出 Hello.class（输出：%s）" % out.strip()[:200])
        return
    with open(cls, "rb") as fh:
        magic = fh.read(4)
    if magic != b"\xca\xfe\xba\xbe":
        fail("生成的 Hello.class 不是合法 class 文件（magic=%r）" % magic)
        return
    proc = subprocess.run([os.path.join(java_home, "bin", "java"), "Hello"], cwd=work, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    run_out = proc.stdout.decode("utf-8", "replace")
    if "JASMIN_OK" in run_out:
        ok("端到端真跑通过：jasmin 汇编出合法 Hello.class 且 java 执行输出 JASMIN_OK"
           "（同时证明 java-cup 运行期可用、包装脚本 classpath 正确）")
        return
    fail("生成的类执行未得到预期输出（exit=%s）：%s" % (proc.returncode, run_out.strip()[:200]))


def check_evidence(pkg):
    java_home = _java_home() or "(未找到 JDK)"
    for rel in (JAR, CUP):
        path = os.path.join(pkg, rel)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            digest = hashlib.sha256(fh.read()).hexdigest()
        ok("证据：%s = %d 字节 sha256=%s…" % (os.path.basename(rel),
                                            os.path.getsize(path), digest[:16]))
    ok("证据：JDK=%s" % java_home)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    if check_artifacts(pkg):
        check_jar_layout(pkg)
        check_end_to_end(pkg)
    check_evidence(pkg)
    print("checks=%d fails=%d skips=%d" % (4, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
