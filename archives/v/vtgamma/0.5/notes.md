# vtgamma 0.5 — 适配记录

## 1. 上游概况

- 项目：`kilobyte/vtgamma` — 为 Linux 虚拟控制台（VT）与 xterm 类图形终端模拟器生成
  伽马校正后的颜色斜坡（gamma correction for virtual terminals）。
- 版本：0.5（tag `0.5`，归档内文件日期 2023-09-14）。
- 语言：单个纯 Perl 脚本（`vtgamma`，4380 字节），无 C/C++ 源码。
- 归档内容（`tar tzf vtgamma-0.5.tar.gz` 全量）：
  `vtgamma-0.5/{.gitignore,LICENSE,README,vtgamma,vtgamma.1}` — 无 `configure`、
  无 `Makefile`、无测试目录、无 CI 配置。
- 许可证：Public Domain（上游 LICENSE 原文声明放弃版权，若司法辖区不允许则授予
  全许可）。

## 2. 源码获取（R39）

| 项 | 值 |
|---|---|
| URL | `https://codeload.github.com/kilobyte/vtgamma/tar.gz/refs/tags/0.5` |
| HTTP | `HTTP/2 200`，`content-type: application/x-gzip` |
| sha256 | `ccdbb779eb25639b46711d2766a8fe310704a3cd6d5d3c728901504e92ddc03f` |

说明：`github.com/kilobyte/vtgamma` 网页端在本机 `curl` 连接超时（DNS/网络可达性
受限），`codeload.github.com` 可达且返回 200；两者指向同一 tag 归档，内容字节一致。
`conan create` 的 `get()` 下载后按 `conandata.yml` 的 sha256 自行校验通过。未使用任何
第三方镜像或 Debian/发行版重打包源。

## 3. 依赖（R36）

唯一依赖：`perl/5.42.2`。

```
$ conan download "perl/5.42.2" -r=ohpcd --only-recipe      # rc=0
Local Cache
  perl
    perl/5.42.2
      revisions
        13c4f5bde5668df0b7268c4d0c01073c (2026-07-30 12:28:48 UTC)

$ conan install --requires=perl/5.42.2 -r=ohpcd \
    -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=never
perl/5.42.2: Already installed! (1 of 1)                 # OHOS/armv8 二进制已发布
```

制品仓中已有 perl/5.42.2 的 OHOS armv8 二进制，无缺失依赖。

## 4. 配方行为

上游没有构建系统，`conanfile.py` 的 `build()` 只做两件事：

1. 读取上游 `vtgamma`，断言首行 shebang 与预期一致
   （`#!/usr/bin/perl -w`；不一致即抛 `ConanException`，防上游漂移后静默适配）；
2. 把 shebang 改写为 `#!/usr/bin/env perl`，输出到 `build/install/bin/vtgamma`，
   并把 `vtgamma.1` 复制到 `build/install/share/man/man1/`。

`package()` 将 `bin/vtgamma`、`share/man/man1/vtgamma.1`、`licenses/LICENSE` 收进包。

改写 shebang 的理由：上游 shebang 写死 `/usr/bin/perl`，而 HarmonyOS PC 的 perl 位于
`/data/service/hnp/bin/perl`（hnp 包管理路径），写死路径在目标机上不存在。改用
`env perl` 后由 PATH 解析解释器，与包内声明的 Conan 运行时依赖 `perl/5.42.2`
（`VirtualRunEnv` 会把该包的 `bin/` 加入 PATH）配合，实现可重定位。

## 5. 构建与验证

- 交叉编译（WSL，host=OHOS/armv8/clang15/libc++/cppstd17，build=x86_64 Linux）：
  `/root/ohpcd-work/build/vtgamma-0.5`，
  `conan create . -pr:h ohos-aarch64-wsl-xbuild -pr:b default --build=missing`。
- 产物：`bin/vtgamma`（Perl 脚本，mode 755，首行 `#!/usr/bin/env perl`）、
  `share/man/man1/vtgamma.1`、`licenses/LICENSE`。
- `test_package`（R34 实质消费者测试）：校验 `bin/vtgamma` 存在、shebang 已改写，
  并在可执行环境下用 perl 对安装后的脚本做 `perl -c` 语法校验。

## 6. 元数据

- 本包含 `bin/` 可执行文件，按 R38 / CI L0k 在软件级目录提供
  `archives/v/vtgamma/commands.json`（`type: tool`）。
- `archives/v/vtgamma/0.5/manifest.yaml`：版本级 manifest。
- 上游无测试设施，`test_package/MANIFEST.yml` 的 `upstream_official_tests: []`
  与 `adapted_tests: []` 为如实记录，未编造上游测试框架名。

## 7. 已知限制 / 待人工

- `vtgamma` 的正常工作路径需要真实 VT/终端（`ioctl` 操作控制台），自动化环境无法
  完全复现其终端设置流程；自动化验证覆盖到脚本安装形态与 Perl 语法/解释器可执行性。
- 该包为纯 Perl 脚本，`commands.json` 标记 `binary: false`（无编译产物）。
