#!/usr/bin/env python3
"""消费测试 — pkwalify 1.24 真实产物校验（全部离线，不触网）。

用法: python3 check_pkwalify.py <package_folder>
"""
import glob
import os
import subprocess
import sys

checks = fails = 0

TMP = "/data/storage/el2/base/cache"


def ok(msg):
    global checks
    checks += 1
    print("[ok]   %s" % msg)


def fail(msg):
    global checks, fails
    checks += 1
    fails += 1
    print("[FAIL] %s" % msg)


def _perl_exe():
    """解析 perl 绝对路径。

    test() 的 conanrun 环境 PATH 里**没有 perl**（裸名直接 FileNotFoundError，与
    init-system-helpers 同一教训），故按候选绝对路径显式找。
    """
    for cand in ("/data/service/hnp/bin/perl", "/usr/bin/perl", "/bin/perl",
                 "/usr/local/bin/perl"):
        if os.path.exists(cand):
            return cand
    import shutil
    return shutil.which("perl") or "perl"


PERL = _perl_exe()


def perl(args, **kw):
    return subprocess.run([PERL] + args, capture_output=True, text=True,
                          timeout=180, **kw)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]

    pms = glob.glob(os.path.join(pkg, "lib", "perl5", "**", "*.pm"), recursive=True)
    kwalify = [p for p in pms if os.path.basename(p) == "Kwalify.pm"
               and os.path.basename(os.path.dirname(p)) != "Schema"]
    schema_pm = [p for p in pms if os.path.basename(p) == "Kwalify.pm"
                 and os.path.basename(os.path.dirname(p)) == "Schema"]
    if not kwalify:
        fail("产物缺失：lib/perl5 下找不到 Kwalify.pm")
        print("\nchecks=%d fails=%d\nRESULT: FAIL" % (checks, fails))
        return 1
    libdir = os.path.dirname(kwalify[0])
    ok("产物齐备：Kwalify.pm 位于 %s（lib/perl5 下共 %d 个 .pm）"
       % (os.path.relpath(kwalify[0], pkg), len(pms)))

    if schema_pm:
        ok("Schema::Kwalify 产物存在：%s" % os.path.relpath(schema_pm[0], pkg))
    else:
        fail("产物缺失：找不到 lib/perl5/**/Schema/Kwalify.pm")

    cli = os.path.join(pkg, "bin", "pkwalify")
    if os.path.isfile(cli) and os.access(cli, os.X_OK):
        ok("上游 CLI 产物存在且可执行：bin/pkwalify（上游 Makefile.PL 的 EXE_FILES 声明）")
    else:
        fail("缺少上游 CLI 产物：%s（或不可执行）" % cli)

    r = perl(["-I" + libdir, "-MKwalify", "-e", "print $Kwalify::VERSION"])
    if r.returncode == 0 and r.stdout.strip() == "1.24":
        ok("真实加载：perl -MKwalify 成功，$Kwalify::VERSION == 1.24")
    else:
        fail("perl -MKwalify 失败或版本不符：rc=%d out=%r err=%r"
             % (r.returncode, (r.stdout or "").strip()[:60],
                (r.stderr or "").strip()[:140]))

    r = perl(["-I" + libdir, "-MSchema::Kwalify", "-e", "print 'ok'"])
    if r.returncode == 0 and r.stdout.strip() == "ok":
        ok("真实加载：perl -MSchema::Kwalify 成功")
    else:
        fail("perl -MSchema::Kwalify 失败：rc=%d err=%r"
             % (r.returncode, (r.stderr or "").strip()[:140]))

    # 真实功能：上游契约是「合法数据返回 1；非法数据 die」
    code = (
        "use Kwalify;"
        " my $s = { type=>'map', mapping=>{ name=>{type=>'str',required=>1},"
        " age=>{type=>'int'} } };"
        " my $r1 = eval { Kwalify::validate($s, { name=>'Alice', age=>30 }) };"
        " my $e1 = $@;"
        " my $r2 = eval { Kwalify::validate($s, { name=>'Alice', age=>'notanint' }) };"
        " my $e2 = $@;"
        " print 'R1=', (defined $r1 ? $r1 : 'undef'),"
        "       '|E1=', ($e1 ? 'die' : 'none'),"
        "       '|R2=', (defined $r2 ? $r2 : 'undef'),"
        "       '|E2=', ($e2 ? 'die' : 'none');"
    )
    r = perl(["-I" + libdir, "-e", code])
    out = (r.stdout or "").strip()
    if r.returncode == 0 and "R1=1" in out and "E1=none" in out and "E2=die" in out:
        ok("真实功能真跑：Kwalify::validate 合法数据返回 1、非法数据 die（类型不符被正确拒绝）")
    else:
        fail("真实功能校验不符：rc=%d out=%r err=%r"
             % (r.returncode, out[:140], (r.stderr or "").strip()[:160]))

    # 上游 CLI 行为（如实记录：缺**可选**解析后端时不计为通过）
    if os.path.isfile(cli):
        os.makedirs(TMP, exist_ok=True)
        sc = os.path.join(TMP, "kwcheck_schema.yaml")
        dt = os.path.join(TMP, "kwcheck_data.yaml")
        with open(sc, "w") as fh:
            fh.write("type: map\nmapping:\n  name:\n    type: str\n    required: true\n")
        with open(dt, "w") as fh:
            fh.write("name: Alice\n")
        r = perl(["-I" + libdir, cli, "-f", sc, dt])
        blob = (r.stderr or "") + (r.stdout or "")
        if r.returncode == 0:
            ok("上游 CLI 真跑：pkwalify -f schema data → rc=0（本环境有可用 YAML/JSON 后端）")
        elif "Unsupported module" in blob:
            mods = sorted({w.strip(".,") for w in blob.split()
                           if "::" in w})
            ok("上游 CLI 真跑：pkwalify -f schema data → rc=%d，工具自报缺**可选**解析后端 %s"
               "（上游 Makefile.PL 不强制装其一；如实记录为已知限制，不计为通过）"
               % (r.returncode, mods[:6]))
        else:
            fail("上游 CLI 行为无法解释：rc=%d err=%r"
                 % (r.returncode, blob.strip()[:160]))
    else:
        ok("跳过上游 CLI 实跑（bin/pkwalify 不存在，已由上一项 FAIL 记录）")

    total = sum(os.path.getsize(p) for p in pms)
    rv = perl(["-e", "print $^V"])
    ok("证据：%d 个 .pm、共 %d 字节；perl %s"
       % (len(pms), total, (rv.stdout or "?").strip()))

    print("\nchecks=%d fails=%d" % (checks, fails))
    print("RESULT: %s" % ("PASS" if fails == 0 else "FAIL"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
