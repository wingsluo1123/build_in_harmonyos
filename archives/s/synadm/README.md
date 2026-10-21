# synadm

- **上游**：https://codeberg.org/synadm/synadm
- **版本**：0.49.2
- **形态**：纯 Python CLI（noarch）——Matrix Synapse homeserver 的管理客户端
- **许可证**：GPL-3.0-or-later（另随包发布 3 个 vendored 依赖的许可证文件）

## 归档内容

```
synadm/
  commands.json            R38/L0k 命令行工具声明（type: "tool"）
  manifest.yaml            软件级 manifest（跨版本适配要点）
  README.md                本文件
  0.49.2/
    conandata.yml          官方 PyPI sdist + 3 个 vendored 依赖（URL/sha256 钉版 + PF4 探测取证）
    conanfile.py           纯 Python 配方（staging + vendoring + PYTHONPATH/PATH 环境注入，零补丁）
    manifest.yaml          版本级 manifest（依赖清单、知识沉淀与引用）
    notes.md               适配笔记（10 条问题/根因/方案、上游测试为 0 的取证、Vendoring 决策）
    patches/               空 —— 上游源码未做任何修改
    reports/test-report.md 63 用例逐项结果 + 关键问题分析
    test_package/
      conanfile.py               消费者入口（优先 OHOS 原生解释器，conanrun 环境下执行）
      MANIFEST.yml               上游 0 用例取证 + 两套件声明（test_type: R34）
      test_synadm.py             42 用例 / 67 断言（通用消费者视角，本地 HTTP stub）
      test_synadm_ohos.py        21 用例 / 47 断言（鸿蒙特有：AF_UNIX、HMDFS、只读 /tmp、原生调用）
```

## 上游测试

上游 **不提供自动化测试**（`upstream_test_count: 0`）：官方 sdist 27 文件无测试、codeberg master
树 79 条目无测试路径、`.forgejo/workflows` 仅 `lint.yaml`（只跑 `flake8 synadm`）与 `release.yaml`。
本包的 63 个用例全部由适配组新增，覆盖上游 API/CLI/打包元数据/格式化器与鸿蒙平台特性，均为 R34
实质测试（断言真实 API 行为，无空壳打印）。取证细节见 `0.49.2/notes.md` 与 `test_package/MANIFEST.yml`。

## 使用

```bash
conan install --requires=synadm/0.49.2 --build=missing
source conanrun.sh                      # 注入 PYTHONPATH 与 PATH，否则 CLI 与依赖都找不到
synadm --version                        # → synadm, version 0.49.2
synadm -c <config.yaml> -o json user list
# 本地 unix socket 管理链路（OHOS 上实测可用），配置键由 synadm 自身写回：
#   protocol: unix
#   base_url: /data/storage/.../synapse-admin.sock   # synadm 内部百分号编码成 http+unix://%2F…
```

配置与日志写用户可写目录（`~/.config/synadm`、`~/.local/share/synadm/debug.log`）；
OHOS 上 `/tmp` 为只读挂载，不要用于任何持久或临时写入。
