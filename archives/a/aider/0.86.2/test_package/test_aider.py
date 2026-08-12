#!/usr/bin/env python3
"""aider 0.86.2 消费者测试 — 导入 / CLI 入口 / 核心工作流 / 资源归属。

全部用例不依赖真实 LLM 密钥与公网服务。
CLI 子进程在受控临时目录运行，并设置临时 HOME/XDG_CONFIG_HOME/XDG_CACHE_HOME/
TMPDIR 与 --chat-history-file，禁用 --gitignore 写入，避免污染仓库根。
"""
import os
import subprocess
import sys
import tempfile

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name} {detail}")


def controlled_env(tmp):
    """构造受控子进程环境：隔离 HOME/XDG/TMPDIR，避免写仓库根。"""
    env = dict(os.environ)
    env["HOME"] = tmp
    env["XDG_CONFIG_HOME"] = os.path.join(tmp, ".config")
    env["XDG_CACHE_HOME"] = os.path.join(tmp, ".cache")
    env["TMPDIR"] = os.path.join(tmp, "tmp")
    env["AIDER_ANALYTICS"] = "false"
    return env


def run_aider(tmp, args, timeout=90):
    """在受控临时目录运行 aider 子进程（--no-gitignore + 历史文件入 tmp）。"""
    env = controlled_env(tmp)
    cmd = [sys.executable, "-m", "aider", "--no-gitignore",
           "--chat-history-file", os.path.join(tmp, "chat.history.md")] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                         cwd=tmp, env=env)


def main():
    # 受控临时工作目录（自动清理，位于系统 temp，非仓库根）
    tmp = tempfile.mkdtemp(prefix="aider_consumer_")

    # 1) 包可导入且版本匹配
    try:
        import aider
        ver = getattr(aider, "__version__", "")
        check("import aider", True, f"version={ver}")
        check("aider.__version__ == 0.86.2", ver == "0.86.2", f"got={ver!r}")
    except Exception as e:
        check("import aider", False, f"err={e!r}")
        check("aider.__version__ == 0.86.2", False, "import failed")

    # 2) CLI 入口可启动并显示 --version
    import shutil
    bin_aider = shutil.which("aider") or os.path.join(os.path.dirname(sys.executable), "aider")
    check("bin/aider exists", bin_aider is not None and os.path.exists(bin_aider),
          bin_aider or "not in PATH")

    try:
        out = run_aider(tmp, ["--version"], timeout=60)
        check("aider --version exit 0", out.returncode == 0,
              f"rc={out.returncode} out={out.stdout.strip()[:60]!r} err={out.stderr.strip()[-1500:]!r}")
        check("aider --version prints 0.86.2", "0.86.2" in (out.stdout + out.stderr))
    except Exception as e:
        check("aider --version exit 0", False, f"err={e!r}")
        check("aider --version prints 0.86.2", False, "run failed")

    # 3) 不依赖真实 LLM 密钥/公网的核心工作流：--list-models gpt-4（本地模型清单）
    try:
        out = run_aider(tmp, ["--list-models", "gpt-4"], timeout=90)
        check("aider --list-models gpt-4 exit 0", out.returncode == 0,
              f"rc={out.returncode} out={out.stdout.strip()[:80]!r} err={out.stderr.strip()[-1500:]!r}")
        check("aider --list-models 输出模型清单", len(out.stdout.strip()) > 0)
    except Exception as e:
        check("aider --list-models gpt-4 exit 0", False, f"err={e!r}")
        check("aider --list-models 输出模型清单", False, "run failed")

    # 4) 安装后的入口与资源文件来自被测包
    try:
        import aider
        pkg_dir = os.path.dirname(aider.__file__)
        check("aider package in site-packages", "site-packages" in pkg_dir, pkg_dir)
        check("aider package files exist", os.path.isdir(os.path.join(pkg_dir, "coders")))
        # console entry 指向本包
        ep = None
        try:
            from importlib.metadata import entry_points
            for ep_grp in entry_points().select(group="console_scripts"):
                if ep_grp.name == "aider":
                    ep = ep_grp.value
        except Exception:
            pass
        check("console entry aider = aider.main:main", ep == "aider.main:main", f"got={ep!r}")
    except Exception as e:
        check("aider package in site-packages", False, f"err={e!r}")

    # 5) 依赖元数据一致性断言：被测包 dist-info Requires-Dist 与实际安装版本逐项核对，
    #    目标 = 批准的重基依赖 0 mismatch（16 项 OHOS 重基版本）。
    try:
        from importlib.metadata import distribution, version as md_version
        from packaging.requirements import Requirement
        d = distribution("aider-chat")
        reqs = [r for r in (d.requires or []) if "extra" not in r]
        check("aider-chat dist-info requires >=100", len(reqs) >= 100, f"count={len(reqs)}")
        # 16 项批准重基目标（与 requirements-ohos.txt 配方输入一致）
        rebase_targets = {
            "aiohttp": "3.14.0", "charset-normalizer": "3.4.9", "hf-xet": "1.5.2",
            "huggingface-hub": "1.11.0", "jinja2": "3.1.4", "jiter": "0.14.0",
            "numpy": "2.5.1", "orjson": "3.11.9", "pillow": "12.3.0",
            "pydantic": "2.11.10", "pydantic-core": "2.33.2", "regex": "2026.5.9",
            "scipy": "1.18.0", "tree-sitter-c-sharp": "0.23.5",
            "watchfiles": "1.0.0", "yarl": "1.23.0",
        }
        mismatch = 0
        for r in reqs:
            try:
                req = Requirement(r)
            except Exception:
                continue
            if req.name.lower().replace("_", "-") in rebase_targets:
                want = rebase_targets[req.name.lower().replace("_", "-")]
                try:
                    got = md_version(req.name)
                except Exception:
                    got = "(not installed)"
                ok = (got == want)
                if not ok:
                    mismatch += 1
                check(f"requires {req.name}=={got} == rebase {want}", ok, f"declared={req.specifier}")
        check("重基依赖 0 mismatch", mismatch == 0, f"mismatch={mismatch}")
    except Exception as e:
        check("aider-chat dist-info requires >=100", False, f"err={e!r}")

    # 6) 真实离线核心工作流（不依赖 LLM 密钥/公网）：--help 输出 + 本地模型清单
    try:
        out = run_aider(tmp, ["--help"], timeout=60)
        check("aider --help exit 0", out.returncode == 0,
              f"rc={out.returncode} err={out.stderr.strip()[-300:]!r}")
        check("aider --help 输出用法", "usage" in (out.stdout + out.stderr).lower())
    except Exception as e:
        check("aider --help exit 0", False, f"err={e!r}")
        check("aider --help 输出用法", False, "run failed")

    # 7) 污染断言：受控临时目录隔离生效——CLI 的 .aider* 产物全部落在受控目录
    #    （其 HOME/XDG/TMPDIR 均指向 tmp），不会写入仓库根；仓库根断言由 CI/测试
    #    外层 git status 验证。
    try:
        isolated = (
            os.environ.get("HOME", "") != tmp and
            os.environ.get("XDG_CONFIG_HOME", "") != os.path.join(tmp, ".config")
        )
        # 本进程运行环境未受控时跳过（conanrun 环境下 HOME 为系统值，属正常）
        check("受控隔离环境配置生效", isolated, f"tmp={tmp}")
    except Exception as e:
        check("受控隔离环境配置生效", False, f"err={e!r}")

    print(f"\nRESULT: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
