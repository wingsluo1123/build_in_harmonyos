#!/usr/bin/env python3
"""lddtreepax test_package — 对真实 aarch64 ELF (/bin/sh) 的实质断言 (R34).

显式路径 + 直接执行已安装 lddtreepax（验证 shebang #!/usr/bin/env python3 可用），
PYTHONPATH 显式指向 pyelftools site-packages（不依赖 conanrun 环境注入）。

断言：
1. 被测包内存在可执行 lddtreepax（provenance）
2. pyelftools site-packages 可定位（PYTHONPATH 来源）
3. rc=0（工具在 OHOS/musl 上可运行）
4. 输出含 interpreter 行（真实解析了 PT_INTERP）
5. 输出含 libc.so 行（真实解析了 DT_NEEDED；musl 布局下该库无 soname 链、
   解析路径打印 None，但 DT_NEEDED 条目本身必须出现——空输出/报错都过不了）
"""
import glob
import os
import subprocess
import sys


def main():
    ldd_pkg, pyelf_pkg = sys.argv[1], sys.argv[2]

    exe = os.path.join(ldd_pkg, "bin", "lddtreepax")
    assert os.path.isfile(exe), f"被测包内无 lddtreepax: {exe}"
    sites = glob.glob(os.path.join(pyelf_pkg, "lib", "python*", "site-packages"))
    assert sites, f"pyelftools site-packages 未找到 under {pyelf_pkg}"

    env = dict(os.environ)
    env["PYTHONPATH"] = sites[0] + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([exe, "/bin/sh"], capture_output=True, text=True,
                       env=env)
    assert r.returncode == 0, \
        f"lddtreepax /bin/sh rc={r.returncode}, stderr={r.stderr!r}"
    assert "(interpreter =>" in r.stdout, \
        f"缺 interpreter 行: {r.stdout!r}"
    assert "libc.so" in r.stdout, \
        f"缺 libc.so DT_NEEDED 行: {r.stdout!r}"

    print("[test_package] PASS: lddtreepax /bin/sh（shebang 直接执行）")
    for line in r.stdout.splitlines():
        print("  " + line)


main()
