# IRAF 2.18.1 / HarmonyOS PC AArch64

任务 7507，分支 `feat/iraf-2.18.1`，申请人 `frj__`。申请路径 C 候选，
基础适配与知识贡献同时提交；最终路径和分值由评审委员会确认。

## 源码与构建范围

官方 tag 归档：<https://github.com/iraf-community/iraf/archive/refs/tags/v2.18.1.tar.gz>。
SHA256：`d4e0859088459622625d27b5c025524dc70fbf334e8df5e59dd32b65630e7981`。
配方使用上述官方 GitHub archive 单值地址，以触发仓库 CI 的 GitHub 镜像回退。
该地址实测重定向至官方 codeload，归档为13,830,889字节，摘要与早期直接下载一致。

上游源码实际含 563 个 C、4872 个 SPP `.x`、1114 个 Fortran `.f`、454 个
generic `.gx` 和 1 个 `.S`。构建先生成无 VOS 的宿主工具及捆绑 F2C，
再编译 VOS、用 VOS 重建工具，最后构建核心和 NOAO。无需外部 Fortran 编译器。

依赖 `readline/8.3`、`zlib/1.3.1`，readline 传递引入 `ncurses/6.6`。
构建工具为 `flex/2.6.4.2`、`bison/3.8.2`、`m4/1.4.19`，均使用已发布制品。

```sh
conan create archives/i/iraf/2.18.1 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

## 关键适配及机制

| 改动 | 原始问题 | 修复与验证入口 |
|---|---|---|
| `zsvjmp.S` 与声明 | AArch64 直接跳转 glibc 私有 `__sigsetjmp`；生产 C/SPP 调用者缺少二次返回属性 | 链接探测选择真实可用的 `sigsetjmp` / `__sigsetjmp`，保留尾跳转和缓冲布局；在生产头与 F2C 生成 C 的公共头补 `returns_twice`；使用实际声明及宏验证 |
| libf2c | `__linux__` 分支包含不存在的 `fpu_control.h` | `__has_include` 按实际头文件能力选择既有路径；保留 Fortran 翻译和数值计算 |
| `f77.sh` | 写死 `/tmp/stderr_*`；EXIT trap 的旧 `rc=0` 覆盖 F2C 失败 | stderr 遵从 TMPDIR，清理保留原状态并输出编译器诊断；实测坏 Fortran 和坏 CC 参数均失败 |
| `xc.c` | 用硬链接落盘程序，HMDFS 拒绝；`-N` 另写死 `/tmp` 和 `/bin/cp` | 普通链接后检查 rename；`-N` 使用 TMPDIR、关闭 mkstemp 描述符、检查 stdio 复制结果 |
| ECL | 初始化拼接文件写死 `/tmp/envcl`；启动器 `-c/-e` 用错 `irafbin` | 使用 VOS `tmp$`；修正为已定义的 `bin` |
| 宿主工具安装 | 二阶段覆盖可执行文件时普通 cp 返回 EPERM | 安装规则用 `cp -f`，保留原复制目标与权限选项 |
| `zfioks.c` | libc 不提供 BSD `rcmd`；该协议所需的 1023 端口在真机被拒绝 | 兼容调用转为实际 SSH 双向通道；默认 RSH 命令为 SSH，保留现有 daemon/callback 路径 |
| `tmerge.x` | 两个不同任务的 `tm_copy` 都生成强符号 `tmcopy_`，lld 拒绝重复定义 | 表合并任务的内部函数改为独立六字符名称 `tmrcpy`；新增消费者验证四值追加 |
| `tiimage` | 原类型判断取错列指针且反向判断；仅读首行却按整个图像长度复制；父过程遗漏错误传播 | 正确检查列类型，逐行读写并检查 EOF，补充必要 errchk；验证 8×8 的全部 64 像素及类型拒绝 |
| ECL 错误恢复 | 上游 `error` 恢复分支提前弹栈/关闭脚本；`iferr` 未保存 ELSE 决策所读的下一 token，IF 的全局缓冲还会跨任务误读 | 区分脚本与外部任务的退出生命周期；预读文本退回所属 FIO 流并检查结果；回归恢复顺序、后续语句、abort、bye |
| 文件保护 | HMDFS 拒绝保护标记的硬链接 | 使用绝对 symlink 作为 IRAF 内部删除保护标记；保留 stat 的 dev/inode 判定 |
| Makefile 安装 | 默认写全局 `/etc/iraf` | 参数化 sysconfdir，Conan 包仅写自身 `etc/iraf` |

### 构建工具环境

Bison 制品的 `yacc` 包装器和数据目录使用安装前缀常量。配方在私有 build
目录生成 `yacc -> bison -y` 入口，并设置 `BISON_PKGDATADIR` 与实际 `M4` 路径。
通过 make 命令行 PATH 保证该入口在 VirtualBuildEnv 激活后仍优先。

`f77_parallel.py` 仅在构建期把独立 Fortran 源文件交给每次调用最多 4 条编译管线。
每个进程仍调用原始 F77/F2C 命令，错误逐一检查；链接、混合源与 `-o` 模式直接
委托原脚本。打包不携带此调度器，安装后的编译器使用上游 F77 脚本。

外层 make 与内部调度器均读取 `tools.build:jobs`（1～4）；这不是全机进程数上限。
启动进程遇到 ENOMEM/EAGAIN 时停止派发，排空已启动任务后串行处理未启动输入，
串行启动最多尝试 4 次，等待间隔 0/2/5/10 秒。已经启动的编译器非零退出不会重试，
启动重试耗尽也使构建失败；线程创建失败等其他资源异常仍会严格失败。
该逻辑不能替代真机内存容量，也不把有界重试记为编译测试通过。

另一轮在3170秒出现一次 `f2c.e: Operation not permitted`，当时仍有约89万inode和
5.5GB可用内存。同一文件随后经Python、原始posix_spawn和直接shell各三次执行均成功，
根因尚未证实。构建期 `f2c_launcher.py` 仅在真正F2C的Popen构造抛出EPERM时
尝试三次启动（等待0/1/3秒）；进入wait之后的编译器退出、信号或wait错误均不重试。
参数、工作目录、环境和标准流继承原调用；真实编译器非零退出保持失败。
该启动器不安装进包，安装后的F77/F2C入口保持原路径。
启动边界故障注入11/11，真机有效Fortran生成AArch64对象及坏Fortran拒绝2/2通过；
坏输入测试预置旧C文件，仍不生成对象，验证没有用旧翻译结果掩盖错误。

### 编译和链接能力探测

补丁不增加操作系统平台宏。配方先验证编译器可正常链接，再探测实际 `sigsetjmp`
和备用 `__sigsetjmp` 符号；不用setjmp.h宏别名代替符号检测。通过通用
`IRAF_SIGSETJMP` 宏传入汇编，保留尾跳转及状态前缀缓冲ABI，两者均不可用时直接失败。
rcmd以netdb.h声明及实际链接结果判断，仅缺失时启用 `IRAF_USE_SSH_RCMD` 的实质SSH实现。
libf2c按 `__has_include(<fpu_control.h>)` 使用头文件能力，保留上游通用路径。

每个探针直接设置自己的可写TMPDIR，不依赖外层CI环境；只编译和链接，不执行探针。
只有明确的目标符号/声明/头缺失才可选择兼容路径。权限、只读目录、配额、文件描述符、
资源或信号错误及同屏额外链接错误必须失败，不能用兼容路径掩盖。真机24项专项测试包含
混合错误、缺失接口、正常driver汇总以及外层TMPDIR未设/只读的真实SDK负控。
配方还在build目录生成SDK ar/ranlib/nm/strip入口；W3与受控消费PATH均不使用旧手工别名。

## 测试清点与结果入口

上游 `test/*.md` 有 **136 个独立命令块**。原始 `make test` 先用 ECL 执行
全部块，再用经典 CL 重复 `cl.md` 的 7 块，共 **143 次调用**。
输入文件块不计测试。test-syntax.md 第 152 行起的失败输出示例虽含 cl>，
但由 `File: printed on stdout` 指定为数据块，不能计入独立测试。原始 xfail、无限循环 skip 和 macintel 架构选择均保留；
实际 passed / xfailed / skipped 分类见 `reports/test-report.md`。

`build()` 必须完成原始两次测试入口，并检查两条 summary 与 143 的总数；
任一真正 failed、缺少 summary 或清点不一致都会使构建失败。

安装消费者为 **16 个场景、33 项检查**：版本、CL/ECL、8×8 常数图像统计、
IRAF OIF → FITS → OIF 往返、完整 SPP 编译运行、错误恢复、生产声明及宏的 6 项跳转检查、
坏 Fortran 失败传播、5 项 SSH 通道检查、`xc -N`、ECL 初始化拼接、表合并/图像数组回归及保护文件删除/解除保护。
它们调用安装包的程序和 `libos.a`，不是替身实现。

上游 `utilities.nttools.md` 的 tmerge/tiimage 仅有标题，没有可执行用例；
对应功能由新增消费者实际覆盖。ECL 两处修复属于上游执行与 grammar 集成缺陷，
在本次重新生成 parser 和补充错误恢复用例时暴露，不归因为 OHOS 独有问题。

消费者由仓库 CI 已使用的 zsh 启动；目标机系统 sh 在 here-document 处理时
仍尝试写只读 /tmp，不能仅靠脚本内设置 TMPDIR 避开。断言和输入保持不变，
修正启动方式后从实际安装包完整通过 16 场景、33 检查。

构建、上游和消费者的实测记录、日志摘要及 SHA256 见 `reports/`。

## 安装与运行边界

独立缓存消费曾在真实的三层 `noaobin$` 及 `(arch)` 展开时失败，绝对文件路径和
直接执行均正常。上游 `vfn_expand_ldir` 使用255字符的累计池且弹栈后不回收，
较长包前缀使无递归路径也触发递归错误。修复按现有路径长度/嵌套深度分配有界池，
保存并回收子段起点，补齐环境值拼接后的容量检查；保留16层递归和输出长度界。
隔离生产 `libsys.a`/ECL 对照为原7/9、新9/9，详见机制证据。
逻辑目录展开仍遵守上游 `SZ_OSDIR=255`、`SZ_PATHNAME=511` 的限制。

使用 Conan 运行环境中的 `irafcl`、`cl`、`ecl`、`xc`、`mkiraf` 等 `bin` 入口。
这些启动器相对确定包根目录，设置 IRAFARCH，并创建可写临时目录；默认
`$HOME/.cache/iraf/tmp`，可由 `TMPDIR` 覆盖。官方 setup.* 辅助脚本保留上游
配置方式；包重定位的受测入口为 `bin` 启动器。

`zlib` 显式声明为运行期需求：安装后的 `xc` 会链接新的 SPP 程序，必须取得
其静态归档。运行环境只为 `xc` 传播 zlib 的 include/lib 元数据；构建 IRAF
本体所用的 readline/ncurses 不作为新程序的隐式链接项。Conan 会跳过普通
application 的静态依赖，因此仅在原构建缓存中测试不足以验证消费声明。
SPP 消费者还需
可用的本机 C 编译器；测试通过 profile 明确传入 SDK clang，未依赖混入的系统 zlib。

SSH 远程内核需要用户配置 SSH 兼容客户端和目标认证；`KSRSH` 可指向配置包装器。
旧 `rcmd` 兼容调用在 OHOS 使用 SSH 认证和端口配置，不声称保留 BSD 保留端口线协议。
默认 daemon/callback 从 4999 起绑定，真机已验证此端口可用。
本次自动测试验证本地可控传输 fixture，没有连接未授权远程服务器。

交互式 X11/图像显示需要外部显示服务器和终端配置；本次验证为无头科学计算流程。
libf2c 的非默认 `-trapuv` 硬件浮点异常启用沿用上游未知 libc 的通用分支，
不把该诊断开关记作已验证功能；未为此删减上游默认测试。

HMDFS 的 symlink 保护标记不等价于 hardlink 备份：原文件被系统工具删除后不能保留数据，
移动包含受保护文件的整个目录也可能使绝对标记失效。本次保证的是受测的 IRAF 内部删除保护。

## 知识复用与新增草稿

复用 E002 的可写临时目录原则、E079 的 HMDFS 硬链接限制。
E1086已覆盖私有glibc类型/宏迁移通则；新增草稿只申报手写上下文汇编及生产双声明层契约。
`fpu_control.h` 在 BCFF 草稿已有相近记录，不重复申报新知识。
新增配对草稿为 `DRAFT-ohos-assembly-glibc-private-sigsetjmp`，区分原始汇编的
libc 符号契约与预编译二进制不兼容，并附独立 libc-test 的 8 项检查。
查重基线和相邻条目边界在草稿内逐条列出。

## 最终状态

本轮源码 `7646521e2988cc49ae145a47569724d56f76b572`，main `ad0c1a73eaeeb0807aebf150606a75a9ee950bd0`。
默认3600秒预算、未修改main CI脚本的完整W3退出0，耗时2081秒。
上游140 passed / 2 skipped / 1 xfailed / 0 failed；安装、隐藏原包的重定位及独立缓存
各16场景/33检查通过。能力探测专项24/24独立计数（21项受控回归、3项调用真实SDK，均在真机执行）。详细run_id、输入及制品摘要见verification.json。
#16270/#16376已按用户要求关闭，本轮不依赖它们；线上CI/AI与C/B分类以平台结果为准。
