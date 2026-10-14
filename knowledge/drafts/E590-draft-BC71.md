# E590 — root runner 上 ncurses/6.6 忽略 TERMINFO：terminfo 类 CLI 的 test_package 找不到终端描述

## 错误特征

本地 x86_64 runner（conan create 以 root 运行）上，terminfo/termcap 类程序在 test_package 里
即使 `TERMINFO` 指向 ncurses 包内的 `share/terminfo` 也加载不到终端描述：

```
TERM=vt100 TERMINFO=<ncurses>/p/share/terminfo tgetent=-1 li=-1 co=-1 cm=NULL      # root
TERM=vt100 TERMINFO=<可读副本>               tgetent=1 li=24 co=80 cm=yes        # nobody
```

`qemu-aarch64 -strace` 显示 root 下 ncurses 只查了编译期默认路径（包以 `--prefix=/` 构建）：

```
getuid() = 0
newfstatat(AT_FDCWD,"//share/terminfo",...) = -1 errno=2 (No such file or directory)
```

上层症状因程序而异：vi 克隆（levee）拿不到 `cm` 进入行模式、屏幕宽度 0 无法输入命令，
读到 stdin EOF 后在 `select+read` 循环里空转直到 timeout；其他程序报 `Error opening terminal`。

## 触发条件

- 程序运行期依赖 terminfo（`tgetent`/`setupterm`），链接本仓 `ncurses/6.6`
- 在**以 root 运行**的本地 x86_64 runner 上执行 test_package（W3 / conan-verify）
- 设备 CI 以普通用户运行，不触发

## 根因分析

1. ncurses 在特权进程中不读取终端数据库相关的环境变量：`TERMINFO`、`TERMINFO_DIRS`、
   `$HOME/.terminfo` 都经 `_nc_env_access()` 把关（`access.o` 定义，被 `db_iterator.o`、
   `home_terminfo.o` 引用），uid 0 时只搜索编译期默认路径。本仓 ncurses/6.6 实测如此。
2. 该包以 `--prefix=/` 构建，默认路径是 `//share/terminfo`，构建机上不存在 → `tgetent=-1`。
3. 改用 `unshare --user --map-user=65534` 以非特权 uid 运行时还有第二个坑：用户命名空间内对
   「属主未映射」的文件没有 `CAP_DAC_OVERRIDE`。ncurses 包内 terminfo 文件属主是 CI 构建用户、
   权限 `640`，映射 uid 读不到；root 先复制一份后，副本属主是外部 uid 0（即映射 uid），可读。

## 解决方案

### 推荐方案：uid 0 时用户命名空间 + root 自有的条目副本（只改测试脚本）

```bash
as_user=()
if [ "$(id -u)" = "0" ]; then
    unshare --user --map-user=65534 --map-group=65534 true 2>/dev/null ||
        fail "running as root without user namespaces: ncurses would ignore TERMINFO"
    as_user=(unshare --user --map-user=65534 --map-group=65534)
    mkdir -p "$WORK/terminfo/v"
    cp "$TERMINFO_DIR/v/vt100" "$WORK/terminfo/v/vt100"   # 只复制用到的条目
    TERMINFO_DIR="$WORK/terminfo"
fi
${as_user[@]+"${as_user[@]}"} env TERM=vt100 TERMINFO="$TERMINFO_DIR" ./prog ...
```

- 工作目录、被测文件仍可正常读写（映射 uid 对应外部 uid 0，属主权限生效）；
- 与 qemu 组合无问题（`unshare ... qemu-aarch64 ./prog` 或 binfmt 直接执行均可）；
- 设备 CI 以普通用户运行，不进入该分支，行为与真实用户一致。

### 回退方案

无用户命名空间时用 `setpriv --reuid=65534 --regid=65534 --clear-groups` 降权，但工作目录与
terminfo 副本需改为该 uid 可读写，降权进程也读不到 root 私有目录中的文件。

### 禁止做法

- ❌ 在构建机创建 `/share/terminfo` 或往 `/usr/share/terminfo` 拷数据库迎合默认路径：污染共享构建机，
  并掩盖设备上的真实查找路径问题。
- ❌ 改用 `TERM=dumb` 绕开：程序走无光标寻址分支（vi 克隆进入行模式），测不到真实终端层，甚至卡死。

## 验证

```bash
# 同一探针：root 失败、非特权 uid 成功 → 命中本条
TERM=vt100 TERMINFO=<ncurses>/share/terminfo ./probe
setpriv --reuid=65534 --regid=65534 --clear-groups env TERM=vt100 TERMINFO=<可读副本> ./probe
# 修复后：levee test_package 在 root runner 上 9/9（含 vt100 光标寻址用例 ESC[30;1H）
```

## 适用边界

- 适用：在 root 身份的本地 runner 上验证 terminfo 类 CLI/TUI 的运行期行为。
- 不适用：设备侧「terminfo 数据库不完整/路径不对」（见 DRAFT-E5xx-terminfo-database-bundle、
  DRAFT-E568-mdp-ohos-musl-terminfo-path），那是普通用户也会遇到的数据缺失问题，根因不同。

## 参考

- 实例：`archives/l/levee/4.0/test_package/test.sh`（`as_user` 分支）
- 查重：已有两条 terminfo 草稿均讲数据库缺失/路径；知识库无「uid 0 忽略 TERMINFO」条目
