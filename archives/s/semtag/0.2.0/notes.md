# semtag 0.2.0 适配笔记

## 编译环境
- 构建系统: custom（单文件 Bash 脚本，无构建系统）
- 编译日期: 2026-10-03
- 编译器: 无（无编译步骤；conan profile 为 OHOS aarch64，仅满足 settings）
- 状态: built

## 源码与语言预检
- 上游: https://github.com/nico2sh/semtag ，tag `v0.2.0`，sha256 `37890fc5bbdeba923b51ff615c4e99b002c95d922925ed1efefd117ad7934548`
- 源码包 7 个文件：`semtag`（492 行 Bash）、`semtag_bkp`（旧版脚本副本）、`release.sh`、`release_v2.sh`（维护者自用发布脚本）、`README.md`、`LICENSE`（Apache-2.0）、`.gitignore`。
- 只读语言预判：`detect_language` -> `other`（build_system=none，无 manifest，无可统计源文件）。依据：全部可执行内容为 `#!/usr/bin/env bash` 脚本，是 **Shell 项目**，大赛接受 Shell 适配，用 `lang-preflight --lang other` 如实申报后放行（exit 0，语言匹配）。
- `lang-preflight` 输出 "R46: 终态 result.json 已上报（draft:false），跳过里程碑草稿"：`$HOME` 下残留其他任务的终态回执，不影响本任务；本任务回执用 `--out` 指定路径产出。

## W0 / W0b
- W0：配方无 `requires`。运行时依赖 `bash`(>=4.3)、`git` 是 OS 工具；`conan download git/2.45.2 -r=ohpcd --only-recipe` 成功（git 配方已发布），即使将来要显式声明也不阻塞。
- W0b：仓库无 semtag 历史归档；近邻先例 `archives/c/clitest/0.5.0`（单文件 shell 工具、补丁 shebang、`no_copy_source`、`package_id` 去掉 arch/compiler/build_type），按其结构适配。

## 编译步骤
无编译。`build()` 只做 `apply_conandata_patches` 并校验补丁已落地（shebang 为 `#!/data/service/hnp/bin/bash`）；`package()` 拷贝 `semtag` → `bin/`、`LICENSE` → `licenses/`、`README.md` → `share/doc/semtag/`，尽力 `chmod 0755`（HMDFS 上可能被忽略，测试不依赖执行位）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 安装后的 `semtag` 在鸿蒙上无法直接执行 | shebang 为 `#!/usr/bin/env bash`，鸿蒙没有 `/usr/bin/env`（E037）；bash 在 `/data/service/hnp/bin/bash` | `patches/0001-semtag.patch` 只改第 1 行 shebang，与仓库内 21 个包的补丁、`lynis` 配方同口径 |
| 2 | 脏工作区执行 `semtag getcurrent` 静默退出 rc=1、无任何输出 | 上游 0.2.0 缺陷：`set -euo pipefail` 下 `status=$(check_git_status)`，函数以非零返回，赋值的命令替换随之令脚本退出。最小复现 `bash -c 'set -e; f(){ echo dirty; return 1; }; s=$(f); echo unreachable'` 在 Debian bash 5.2 上同样 rc=1 | 判定为上游行为而非平台差异，**不打补丁**（保持补丁最小）；测试只断言「脏树拒绝打 tag 且不产生 tag」（退出码 + 副作用），不依赖输出文本 |
| 3 | `semtag --version` 输出 `semtag: v0.1.2` | 上游 0.2.0 tag 内嵌 `PROG_VERSION="v0.1.2"`（发布瑕疵） | 不修改；测试用正则 `^semtag: v[0-9]+\.[0-9]+\.[0-9]+$` 而不硬编码 0.2.0 |
| 4 | test_package 在 OHOS run 环境可能找不到 bash/git | conanrun 的 PATH 不含 `/data/service/hnp/bin`（参见知识草稿 `DRAFT-ohos-test-package-bash-absolute-path`） | `test()` 用 `sh` 调测试脚本；脚本内优先 `/data/service/hnp/bin/bash`，并把 `/data/service/hnp/bin` 追加进 PATH |
| 5 | CI 首轮失败：`fatal: detected dubious ownership in repository at .../test_package/semtag-tp-generic/r1`，夹具仓库建不出来 | 设备上 HMDFS 工作目录属主 uid 与运行用户不一致，Git ≥2.35.2 拒绝；`safe.directory` 只认 global/system/命令行配置，仓库本地配置无效；原脚本把 `GIT_CONFIG_GLOBAL=/dev/null` 反而堵死了全局配置（知识 E101/E497，同形先例 `archives/g/git/2.45.2/test_package/test.sh`） | 两个测试脚本改为在私有 `$HOME/.gitconfig` 写入 `[safe] directory = *` 并让 `GIT_CONFIG_GLOBAL` 指向它；本机用 `chown nobody` 的临时仓库复现 dubious ownership 并验证该配置可消除；设备侧以重跑 CI 为准 |

## 源码修改
`patches/0001-semtag.patch`（1 个文件、1 处改动）：`semtag` 第 1 行 `#!/usr/bin/env bash` → `#!/data/service/hnp/bin/bash`。未使用任何平台宏。

## 上游测试清点（R51）
- 清点：源码包 7 个文件，无 `tests/`、无文件名含 `test`、无 Makefile/CMakeLists、无 ctest/pytest/bats 注册、无 CI workflow。上游用例数 N=0，可运行 N′=0，通过率不适用。
- 证据命令：`find . -type f`、`find . -iname '*test*' -o -name Makefile -o -name CMakeLists.txt`（后者无输出）。
- 因此功能验证全部由 test_package 提供（见下）。

## 验证结果（本地实跑，x86 runner）
在打补丁后的脚本副本上实跑 test_package 两个脚本：

```
$ sh test_package/test_semtag.sh      <stage>/semtag -> semtag generic: 19 passed, 0 failed (rc=0)
$ sh test_package/test_semtag_ohos.sh <stage>/semtag -> semtag ohos: 5 passed, 0 failed, 0 skipped (rc=0)
```

对照实验（未打补丁的上游脚本跑 OHOS 脚本）：`FAIL: packaged shebang is #!/data/service/hnp/bin/bash -- got '#!/usr/bin/env bash'`，证明 OHOS 断言能区分补丁前后。

说明：脚本是纯 Bash，没有 ELF 产物，不存在 E544 的 qemu/动态链接问题。上面是 x86 主机原生 bash 5.2.37 + git 2.47.3 的执行结果，**不等于**鸿蒙设备 bash 上的实跑——`/data/service/hnp/bin/bash` 在本机只是指向 `/bin/bash` 的构建机软链。鸿蒙环境下的行为由 CI 的 `conan create`（test_package 在必跑路径上）验证，CI 结果出来后以日志为准。

## test_package（rule12 鸿蒙特有测试）
- `test_package/conanfile.py`：OHOS profile 下 `requires(tested_reference_str)`，`test()` 用 `sh` 分别执行两个脚本，传入已安装包内的 `bin/semtag`。
- `test_semtag.sh`（19 断言）：在测试自建的临时 Git 仓库里真实运行 semtag——tag 读取、SemVer 递增（major/minor/patch/alpha/rc、`-p`、`-v`）、`-o` 不产生 tag、无新提交不打 tag、新提交后创建附注 tag 且 tag 信息含提交日志、脏树拒绝/`-f` 强制、非法命令。
- `test_semtag_ohos.sh`（5 断言，鸿蒙特有）：① 打包后 shebang 为 hnp bash；② hnp bash 真正能执行打包脚本（直接执行优先，HMDFS 执行位不可用时回退显式解释器；hnp bash 缺失则 SKIP）；③④ 无 Git 身份账号下 `semtag final` 创建 tag 并记录 tagger（`setup_git_user` 依赖 `id -u -n` / `hostname`）；⑤ `TMPDIR` 指向不存在目录时仍可运行（`/tmp` 只读，E002）。
- 鸿蒙特有测试数 N=5（`test_semtag_ohos.sh`），与 `test_package/MANIFEST.yml`、PR 正文、知识草稿一致。

## 依赖版本
无 Conan 依赖。运行时：bash ≥ 4.3、git（适配机 bash 5.2.37 / git 2.47.3）。

## 注意事项
- `package_type=application`，`package_id` 去掉 arch/compiler/build_type 保留 os。
- 软件级 `commands.json`（type=tool，命令 `semtag`）、`README.md`、`manifest.yaml` 位于 `archives/s/semtag/`。新增软件首个版本同时触发 PF8（要求软件级文件）与 PF9（拒一切不带版本目录的 archives 路径），属两规则互斥的已知特例，建 PR 时按 W4 约定登记。
