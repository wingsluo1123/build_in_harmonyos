# laniakea

> Suite of tools to manage a Debian-based Linux distribution（Debian 衍生发行版管理套件，LGPL-3.0-or-later）

## 简介

laniakea 是 lkhq 出品的 Debian 衍生发行版管理套件，提供归档仓库管理（lk-archive）、
管理后台 CLI（lk-admin）、密钥管理（lk-keytool）与消息流同步（rubicon/synchrotron）
等工具。上游使用 Meson 构建，纯 Python 实现（0 个 C/C++ 源文件），但 meson.build
强依赖 systemd/apt-ftparchive/bubblewrap 等 Debian 专属工具链。

## OHOS 适配要点

- 任务标记语言 `cpp`，实测源码为纯 Python（R47 语言预检判定 python，按用户决策覆盖走
  Python application 适配，同生态 laniakea-spark 已合入先例）。
- 不跑上游 Meson/pip：全部 src/ 顶层包复制到 `lib/python3.12/site-packages/`，
  bin/ 生成 5 个 CLI 启动器包装（lk-admin/lk-archive/lk-keytool/rubicon/synchrotron）。
- data/ 镜像到 share/laniakea/ 与 lib/python3.12/data/（匹配上游 get_data_file 非 /usr
  开发目录启发式）；package() 生成最小默认 base-config.toml 使无参 LocalConfig() 可发现。
- 系统绑定桩（OHOS 无对应 C 绑定，仅测试期 import 期符号、不伪造）：apt_pkg / gi
  (AppStream) / cryptography / nacl (PyNaCl) / zmq (pyzmq)。
- bin/ 启动器内置 pwd 占位条目兜底：沙箱/容器 uid 无 /etc/passwd 条目时
  ensure_laniakea_master_user 的 pwd.getpwuid() 不崩溃（走警告分支）。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| python | 3.12.9 | conan 依赖（ohpcd 制品仓已发布） |
| sqlalchemy / tomlkit / python-debian / requests / cryptography / marshmallow / pyzmq / PyNaCl / PyYAML / Pebble / click / rich / firehose | — | 消费环境提供（test_package 按固定/最低版本 pip 安装验证） |

## 功能验证

```bash
lk-admin --version      # 0.1.1
lk-archive --version    # 0.1.1
lk-keytool --version    # 0.1.1
rubicon --version       # 0.1.1
synchrotron --version   # 0.1.1
```

## 参考

- [官方文档](https://laniakea-hq.readthedocs.io/)
- [上游仓库](https://github.com/lkhq/laniakea)
