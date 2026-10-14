# zvbi 0.2.44 适配笔记

## 任务来源

- 平台任务 contrib-12427（开源鸿蒙PC专项积分赛），分支 `feat/zvbi-0.2.44`，2026-09-27 认领（API 留证：open→assigned，claimer=Ember5843）
- 上游：github zapping-vbi/zvbi v0.2.44（2026-08 仍活跃），sha256=bca620ab670328ad732d161e4ce8d9d9fc832533cb7440e98c50e112b805ac5e
- 语言实测（R47 lang-preflight）：**C**（.c 主体，autotools；平台 lang 字段标 cpp 不作数，已源码实测）

## 选库核验（§3.2 否决线）

1. 他人已移植：main 档案无 zvbi（精确+模糊）；制品仓 conan list "zvbi/*" -r=ohpcd = 0；同版本无他人 claim
2. 语言/构建生态：纯 C + autotools；iconv 硬依赖（musl 自带，设备冒烟通过）；libpng/X11/V4L/DVB 均条件化可禁用
3. 可行性：高（VBI 解码库，小体量，零外部依赖）
4. 难度定级：A（纯编译适配，零补丁；设备端 autoreconf 自举属工具链补齐非源码改动）

## 降级边界声明

- V4L/V4L2/DVB/bktr/proxy/X11 后端全部禁用（平台无 VBI 采集硬件；各有干净 off 开关）
- libpng/zlib 不引入（PNG 页面导出功能缺失，configure 自动 HAVE_PNG=no 降级）
- NLS 自动关闭（平台无 gettext，`AM_GNU_GETTEXT([external])` 探测后 USE_NLS=no）
- 上游测试 11 TESTS 未在**构建内**执行（conan build() 传 --disable-tests，R51 如实申报，见 test_package/MANIFEST.yml）；2026-10-08 已在**设备侧**按同口径实跑全过（见下），另由 12 项断言的消费者测试承担构建内验证

## 上游测试套件实跑（2026-10-08，设备真机，rule4 证据）

- 方法（§6.2 设备侧等价验证）：conan 缓存 bootstrap 树（含上游 autoreconf 产物）按本配方同款 configure 参数重新 configure，**唯一差异是不加 `--disable-tests`**，随后 `make -j1` + `make -C test check`
- 结果：**18 PASS / 0 FAIL / 0 SKIP**（automake 汇总 TOTAL=18），覆盖全部 11 个 TESTS 条目：ctest、cpptest、ctest-c89/gnu89/c94/c99/gnu99、cpptest-cxx98/gnuxx98、test-pdc、exoptest、test-unicode、test-dvb_demux、test-dvb_mux、test-hamm、test-packet-830、test-raw_decoder、test-vps
- **归因更正**：早前"test-pdc/test-dvb_* 需采集硬件、编译变体与 clang 不兼容"的预判**不成立**——这些用例均为数据文件驱动，OHOS clang 亦支持全部 -std 变体，实测全过；test/Makefile.am 的 11 条目在 OHOS 上可 100% 运行
- 构建内仍 `--disable-tests`：不改 CI 行为与时限；MANIFEST.yml 已同步更正归因并记录实跑命令

## 构建要点

- GitHub tag 归档无 configure：tool_requires（automake/1.18 + libtool/2.5.4 + gettext/0.22.5.1 + m4/1.4.19，制品仓均已发布）+ 设备端 `autoreconf -fi` 自举（rnnoise/recode 先例；AUTOPOINT=true 跳过 autopoint 版本检查，ACLOCAL_PATH 指向上游 gettext m4）
- 三元组按 rnnoise 先例用 aarch64-unknown-linux-gnu（设备 config.sub 未必认识 ohos）
- hmdfs umask 077→022（configure 生成物，0 命中即报错）；构建期清空 LD_LIBRARY_PATH；不做 strip；make -j1
- test_package 按 opustags 先例用 VirtualRunEnv + env="conanrun"

## 编译结束

（设备 conan create + conan-verify 结果见 reports/）
