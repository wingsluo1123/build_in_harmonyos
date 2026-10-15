# gif 5.2.2 适配笔记

## 编译环境
- 构建系统: makefile（上游纯 Makefile，无 configure）
- 编译日期: 2026-10-04
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang）+ llvm-ar
- 状态: built

## 编译步骤

giflib 5.2.2 是纯 Makefile 工程。直接以 make 命令行注入 clang 编译器和标志构建库与工具：

```bash
make -j1 CC=clang AR=llvm-ar CFLAGS='-std=gnu99 -fPIC -O2' \
  libgif.a libgif.so gif2rgb gifbuild giffix giftext giftool gifclrmp \
  gifbg gifcolor gifecho giffilter gifhisto gifinto gifsponge gifwedge
```

Conan 配方（archives/g/gif/5.2.2/conanfile.py）在 build() 中从
`tools.build:compiler_executables` conf 取编译器/归档器，把 CFLAGS 通过 make 命令行注入，
然后运行 `make -C tests` 执行上游回归套件。package() 只发布 libgif（.a 或 .so 链）、
gif_lib.h 和 COPYING，不发布 CLI 工具（无需 commands.json，R38 库类型豁免）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游回归套件 giffix-rebuild/giffix-regress 失败 | OHOS head(1) 不支持 GNU 负数扩展 `--bytes=-20`（GNU coreutils 扩展，POSIX head 无此选项），截断 GIF 输入失败 | patches/0001-tests-makefile.patch：用 `wc -c` 取源大小，`dd bs=1 count=$((bytes-20))` 截断，保持"去除末尾 20 字节"测试语义 |
| 2 | conan create 测试阶段 DGifOpenFileName 失败 | test.c 中 ColorMapObject 用了 5 元素初始化器，字段错位使 Colors=NULL/ColorCount=0，编码写出坏 GIF | 改为显式字段赋值（ColorCount=2/BitsPerPixel=1/SortFlag=0/Colors=palette），往返测试通过 |
| 3 | W3 junk_check 误拦 | full 模式扫描整个仓库，命中 main 上其他库历史垃圾（cloog/kics 的 .staging-verified） | 用 JUNK_PR_DIFF=pr.diff 单包口径（9 个交付文件），JC 通过 |
| 4 | 本地无法直连 SourceForge 下载 | 本机沙箱网络受限（GitHub/SourceForge 直连被远端关闭） | 本地验证时 conandata 临时注入权威镜像（sources.voidlinux.org，与官方 tarball SHA-256 完全一致 be7ffbd...），验证后恢复官方 URL 提交 |

## 源码修改

- `patches/0001-tests-makefile.patch`（tests/makefile）：仅替换 giffix 两个目标的
  GNU head 负数字节截断为 POSIX wc/dd，不改库源码、不改工具源码、不加平台宏。
  `patch --fuzz=0` 干净应用，dd 输出与 GNU `head -c -20` 逐字节一致（387/387）。

## 依赖版本

无第三方运行时依赖（纯 libc + libm）。

## 验证结果

- 上游回归套件 `make -C tests`：全部 12 个 regress 目标 + 9 张图片 render 检查通过
  （"No output is good news"），日志 reports/conan-create.log 与本地 make 日志。
- 消费者测试 test_gif：EGif* 编码 3x2 GIF → DGif* 解码 → 逐像素往返验证 6/6 像素一致。
- conan-verify：G1/G2/G3/G4 全通过；conan create（OHOS aarch64 profile）成功。
- W3 本地 CI：build_and_test.sh 通过（L0 pass，L1 测试执行证据，L5 库产物基线），
  .ci-result.json 已写入（exit_code=0，log_sha256=c9ed86deeeb076fab0756208677c14af10e73996235467c17d52f6d08589fac0）。

## 测试统计（双口径）

- source_declared_total: 12 个独立上游回归目标（tests/makefile 的 regress 入口：
  render/gif2rgb/gifbuild/gifclrmp/gifecho/giffilter/giffix/gifinto/gifsponge/giftext/giftool/gifwedge）
  + 1 个消费者用例（test_gif 编码-解码往返）= 13
- configured_executable_total: 13（全部实例化）
- executed_passed_total: 13（12 上游 + 1 消费者）
- 失败 0，未运行 0

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Makefile 构建配方（conf 取编译器，make 命令行注入 flags） |
| conandata.yml | 官方 SourceForge URL + SHA-256 + 补丁声明 |
| patches/0001-tests-makefile.patch | head 负数偏移可移植性补丁 |
| test_package/ | CMake 消费者测试（编码-解码往返） |

## 注意事项

- 本地 W3 需 JUNK_PR_DIFF=pr.diff 单包口径，否则 full 模式误扫 main 其他库历史垃圾。
- 本机沙箱无法直连 github.com/sourceforge.net；网络受限环境的镜像注入须验证后恢复官方 URL。
- package() 显式复制 libgif.so 到 .so/.so.7/.so.7.2.0 三名（上游 install 用 ln -sf 建链，
  conan 环境无 install 步骤，直接复制等价产物）。
---

**编译结束**: 2026-10-04 09:43
**最终状态**: built
