# E545-draft-5C1D — open(path, O_CREAT) 缺 mode 参数：新建文件权限位不确定

## 错误特征

- 工具能正常运行、输出内容正确，但新建的输出文件权限位随机（OHOS aarch64 qemu 实测 `0210`、`0155`、`0055`、`0000`），属主读不了或写不了，之后用普通身份读取报 `Permission denied`
- 编译无任何警告；用 root 跑本地验证时一切正常，所以很容易漏掉
- 消费者用例的失败信息形如：`umask 0022: output file mode is 0055, want 0644`

## 触发条件

- 构建系统：任意（本次是无构建系统的单文件 C 程序）
- 阶段：testing / runtime
- 代码形态：`open(path, flags | O_CREAT)` 只有两个参数（上游 shuffle 1.6：`open(argv[2], O_WRONLY|O_CREAT)`）

## 根因分析

`open()` 是变参函数，仅当 flags 含 `O_CREAT`（或 `O_TMPFILE`）时才读取第三个参数 mode；不传则是未定义行为。musl 以 `va_arg` 取 mode，AArch64 上变参的前几个实参走寄存器，调用点没传就读到之前遗留的值，新建文件的权限位就是「残留值 & ~umask」——这一机理是据 POSIX 与 AAPCS64 做的推断，没有核对 OHOS musl 源码，也没有反汇编确认具体寄存器。推测 glibc/x86 桌面上残留值碰巧无害，所以上游多年未发现（未实测）。实测 OHOS clang 15 用 `-O2 -Wall -Wextra` 编译 shuffle.c 无任何警告（未测 `_FORTIFY_SOURCE`）。

实测（OHOS clang `-static` 重链 + `qemu-aarch64`）：

| 程序 | umask | 新建文件权限位 |
|------|-------|----------------|
| 最小程序，缺 mode | 022 / 0 | 0210 / 0210 |
| shuffle 1.6 未打补丁 | 022 | 0155 / 0055 |
| shuffle 1.6 未打补丁 | 077 | 0000 |
| 最小程序，补 `0644` | 022 | 0644 |
| shuffle 1.6 打补丁（`0666`） | 022 / 077 | 0644 / 0600 |

上表的权限位均为 `qemu-aarch64` 用户态下的观测值，没有在真机上实测；成因是推断（见上）。

## 解决方案

### 推荐方案

给每个带 `O_CREAT` 的 `open()` 补显式 mode，普通数据文件用 `0666`（由 umask 过滤）、私密文件 `0600`：

```diff
-      && (out = open(argv[2], O_WRONLY|O_CREAT)) < 0) syserr(argv[2]);
+      && (out = open(argv[2], O_WRONLY|O_CREAT, 0666)) < 0) syserr(argv[2]);
```

补丁里不要加平台宏（这是源码缺陷，不是平台差异）。`test_package` 用消费者程序先设 umask，再让包内工具新建文件，断言 `stat()` 的权限位（umask 022 → 0644，umask 077 → 0600）；该用例对未打补丁的二进制必须失败。预扫描用 `prescan_pattern` 可在适配前找到这类调用。

### 禁止做法

- ❌ 运行后用 `chmod` 补救，或只在测试里 `chmod` 之后再读
- ❌ 用 `#ifdef __OHOS__` 包住 mode 参数
- ❌ 把断言改成「文件存在」；或用 root 跑测试并以「能读回内容」判通过（root 不受权限位限制）

## 验证

```bash
printf '#include <fcntl.h>\nint main(void){return open("t.out",O_WRONLY|O_CREAT)<0;}\n' > t.c
/data/service/hnp/bin/clang -static t.c -o t && rm -f t.out && (umask 022; qemu-aarch64 ./t); stat -c %a t.out   # 缺 mode: 0210
sed -i 's/O_CREAT)/O_CREAT, 0644)/' t.c && /data/service/hnp/bin/clang -static t.c -o t && rm -f t.out && (umask 022; qemu-aarch64 ./t); stat -c %a t.out   # 补 mode: 0644
```

## 查重

- `engine` 以「open O_CREAT without mode argument musl」检索：最高命中 E039（iconv `//IGNORE`，无关）
- 正式库与草稿库中含 `O_CREAT` 的条目：E523（`fallocate` 验证命令里的三参数 open，无关）、`DRAFT-liblockfile-1.17.1-link-oexcl-lockfile-creation`（`link()` 回退到 `O_EXCL` 创建锁文件，mode 已传入，主题不同）；`variadic` 仅命中编译器宏相关草稿（`##__VA_ARGS__`），与 `open()` 变参无关
- 结论：库内没有「`open(O_CREAT)` 缺 mode 参数」条目

## 关联条目

- 相关：DRAFT-liblockfile-1.17.1-link-oexcl-lockfile-creation（同样涉及 `open(O_CREAT)`，主题不同）
