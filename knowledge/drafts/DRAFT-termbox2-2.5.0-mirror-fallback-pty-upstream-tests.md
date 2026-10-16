# DRAFT-termbox2-2.5.0-mirror-fallback-pty-upstream-tests
> 真机 source() 直连上游 URL 超时时用有序镜像回退（sha256 保持官方原值），终端/TUI 类库以 PTY 注入构造可 headless 运行的上游测试包

## 问题特征（真实日志片段/标记）

**症状一：source() 直连超时（download_unavailable）**

真机 conan source() 阶段下载官方归档 `https://github.com/termbox/termbox2/archive/refs/tags/v2.5.0.tar.gz` 连接超时（connect timeout=30，重试 3 次），conan create 退出码 1，门禁 resolved 链路出现 `v2:compile:download_unavailable`。

**症状二：测试包编译报错（compiler_error）**


/storage/Users/currentUser/preflight/clients/a8b6b434d375/termbox2-2.5.0/test_package/tb_test_os.h:3:27: error: unknown type name 'test'
/storage/Users/currentUser/preflight/clients/a8b6b434d375/termbox2-2.5.0/test_package/tb_test_os.h:3:31: error: expected identifier or '('


门禁新增 `v2:compile:compiler_error`。

**真机能力摘录**


HMBS_PLATFORM_CAPABILITIES={"shell":"/bin/sh","tmpdir":"/storage/Users/currentUser/preflight/clients/a8b6b434d375/runtime/termbox2-2.5.0/tmp","jobs":1,"install_shim":true,"hardlink":0,"symlink":1,"chmod":0,"local_mktemp":1}
HMBS_BUILD_TOOLS={"cmake":{"available":true,"path":"/data/service/hnp/bin/cmake","version":"4.1.2"},"make":{"available":true,"path":"/data/service/hnp/bin/make"},"ninja":{"available":true,"path":"/data/service/hnp/bin/ninja"},"python3":{"available":true,"path":"/storage/Users/currentUser/usr/local/bin/python3"}}
HMBS_CMAKE=/data/service/hnp/bin/cmake
HMBS_MAKE=/data/service/hnp/bin/make
HMBS_NINJA=/data/service/hnp/bin/ninja
HMBS_PYTHON3=/storage/Users/currentUser/usr/local/bin/python3


**门禁链路**：`v2:unknown:unclassified_failure` → `v2:compile:compiler_error` → `v2:compile:download_unavailable` → passed。

## 根因

1. 真机不能直连 github.com。conan 配方的 conandata.yml 若只给单个官方 URL，source() 会直接 ConnectTimeout（connect timeout=30，重试 3 次）后失败。
2. 测试包注释里出现 `test_*/` 序列，其中 `*/` 提前闭合块注释，后续文字被当作 C 代码，clang 报 `unknown type name 'test'`。
3. 终端/TUI 类库的上游测试依赖真实 TTY。输入注入用例用 `tb_init_rwfd(master, slave)`（被测端读 slave、写 master），把注入字节写进 master 后被端读不到，headless 下用例形同虚设。

## 修复方案（rec）

1. `archives/t/termbox2/2.5.0/conandata.yml`：把 `sources.url` 改为有序列表，镜像优先、官方兜底：
   yaml
   sources:
     url:
       - https://gh-proxy.com/https://github.com/termbox/termbox2/archive/refs/tags/v2.5.0.tar.gz
       - https://github.com/termbox/termbox2/archive/refs/tags/v2.5.0.tar.gz
     sha256: 1d7a9811...   # 保持官方归档原值，不得改成镜像归档哈希
   
2. `test_package/tb_test_os.h`：删除导致注释提前闭合的 `test_*/` 序列，修掉 clang 报错（此为单库局部补丁，不作为条目主体）。
3. PTY 注入改用从端 fd：把输入注入用例初始化从 `tb_init_rwfd(master, slave)` 改为 `tb_init_fd(slave)`，让被测端从 slave 读、向 slave 写；删除不再使用的 `tb_os_init_rwfd`。
4. `test_package/test_basic.c`、`test_large_input.c`、`test_mod.c` 同步改用 `tb_init_fd`。
5. 同步更新 `MANIFEST.yml`/`notes.md`/`README.md`/`manifest.yaml`/`conanfile.py` 的审计与文案，上游通过率按真实接入执行（16/16）。
6. 本地验证：Alpine gcc + devpts chroot 编译并运行全部 17 个可执行文件（16 上游移植 + test_api），全部退出码 0（test_basic 12、test_mod 10、test_large_input 5、test_resize 7、test_api 21 断言）。

## 禁止策略

- 禁止 `sources.url` 只保留官方直连 URL 而无镜像回退；也禁止把 `sha256` 改成镜像归档的值。命中 `compile:download_unavailable` / `ConnectTimeout` 即视为踩线。
- 禁止用跳过/裁剪上游测试来规避 PTY 依赖；输入注入必须真正让被测端读到注入字节。

## 与相近条目的边界（查重）

- 与 `HMBS_UPSTREAM_TEST_RESULT` 相关条目（如 ccrtp 将 demo 提升为回归套件）：那条处理“上游测试计数/零证据放行”，本条处理“下载可达性 + 测试可 headless 运行”。
- 与 `hmbs_platform_capabilities`、readonly tmp、compiler error harshness、子包 test_package 计数等条目：这些是相邻主题，均不覆盖“官方 URL 超时→有序镜像回退且 sha256 不变”，也不覆盖 PTY 注入构造上游测试。
- `tb_test_os.h` 注释提前闭合属单库局部补丁，仅作为附带步骤，不作为条目主体。

## 适用判断

- 适用：源码归档托管在 github.com、真机 source() 直连会超时的 C/C++ 库；以及上游测试依赖 TTY/PTY、需要 headless 化的终端/TUI 类库。
- 不适用：已有可达镜像或内网缓存的库；测试本身不依赖 TTY 的库。
