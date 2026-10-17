# OHOS worker 四坑：预设 LDFLAGS 的 -L 劫持、HMDFS 0700 目录写入全拒、libXt 无显示错误路径 SIGSEGV、conandata 补丁版本键控格式

## 命中场景

(1) 任何用 `environment.append()` 追加 -L/-I 的 conan 配方（worker 预设
前缀吃掉解析顺序）；
(2) autoconf/config.status/config.guess/autom4te 全家在 HMDFS 上的
临时目录写入（`umask 077 && mktemp -d` 习语）；
(3) Xt 应用的无显示（headless）运行测试；
(4) conandata.yml 登记补丁（本 OHOS conan 分支的导出格式）。

## 症状（实测，xastir 2.2.4 / OHOS aarch64 / clang 15）

1. 链接产物 DT_NEEDED 出现 `libcurl.so.4` / `libpcre2-8.so.0`（图外
   soname）；运行 `Error loading shared library libcurl.so.4` /
   `Error relocating ... pcre2_*` → 静默 SIGSEGV（rc=139，零输出）
2. `config.guess: can't create .../dummy.c: Permission denied` →
   `cannot guess build type`；
   `config.status: can't create ./confXXXXXX/subs1.awk: Permission denied`
3. `ls -ld` 显示临时目录 `drwx--S---`（0700+setgid）；同进程 `echo > f`
   即 EACCES；umask 022 建的目录完全正常
4. DISPLAY 取消下最小 8 行 `XtOpenDisplay(NULL,…)` 程序静默 SIGSEGV
   （零输出、零 loader 诊断）——不是 "Can't open display"
5. conandata 用补丁文件名当键 → export 后 cache 里没有 patches/ 目录，
   `apply_conandata_patches()` 无声不应用，构建按未打补丁源码进行

## 根因

| 坑 | 机制 |
|----|------|
| -L 劫持 | worker 登录 shell 预设 `LDFLAGS=-L<worker>/usr/local/lib`（内含旧 libcurl.so.4 + 共享 libpcre2-8.so.0）；conan 环境组合预设在先、append 在后 → `-lcurl`/`-lpcre2-8` 解析到 worker 旧库 |
| 0700 写入全拒 | HMDFS 权限检查对 mktemp 的 077 掩码目录（呈现 drwx--S---）拒绝一切写入，即使同进程刚创建；非 ACL 标签问题 |
| libXt 崩溃 | XtOpenDisplay 的无显示错误路径依赖 glibc 行为，OHOS musl 下自身 SIGSEGV（与被测应用无关；musl 预先重定位，闭包完整性无关） |
| 补丁格式 | OHOS conan 2.29.1 私有分支的 export_conandata_patches 只做 `patches.get(conanfile.version, [])`——文件名键控的元数据格式取不到任何条目 |

## 解法

1. **prepend，不要 append**：`generate()` 用 `environment.prepend()` 把
   依赖 -I/-L 与链接视图放到 worker 预设前缀之前；worker 前缀退化为无害
   的尾部兜底。test_package 反向断言 DT_NEEDED 不含 libcurl.so.4 /
   libpcre2-8.so.0。
2. **umask 077 → 022**：生成 configure 后全量替换（含内嵌 config.status
   模板）+ 显式 `--build=aarch64-linux-ohos` 绕过 config.guess。
3. **headless 断言矩阵**：真正的断言是"零动态加载器诊断 + 非零退出"
   （OHOS libc 预先重定位——进入 X 层即证明 DT_NEEDED 闭包装载完成）；
   接受显示错误文本或信号死亡两种形态；另用纯 C 无 X 工具（如
   callpass）做正向功能断言。最小 XtOpenDisplay 程序可独立复现缺陷，
   写进 notes 佐证。
4. **conandata 版本键控**：`patches: {"2.2.4": [{patch_file: …,
   patch_type: …, …}]}`；close-archive 会把合成补丁规范化为
   `000N-<源路径>.patch` 逐文件序列。
5. W3 本地 CI 模拟用 zsh 跑 build_and_test.sh：heredoc 临时文件用
   **TMPPREFIX**（不是 TMPDIR），须指向可写目录，否则
   "can't create temp file for here document: read-only file system"。

## 验证

- conan create 全绿：新 DT_NEEDED = libcurl.so（图内 curl/8.15.0），
  无 pcre2 条目（静态 pcre2/10.48）
- 上游 make check 230/230 真实执行（测试二进制经链接视图 +
  LD_LIBRARY_PATH 满足闭包）
- 消费者测试 6 组断言全过；W3 本地 CI 模拟通过
