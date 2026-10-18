# E2297 — toybox coreutils 不支持 GNU 长选项导致上游 shell 测试失败

## 错误特征

```text
stat: Unknown option 'printf=%s'
cmp: Unknown option 'bytes='
cmp: Unknown option 'ignore-initial='
```

## 触发条件

- 平台：OHOS / HarmonyOS（/bin 下为 toybox）
- 阶段：testing（运行上游 `make check` 的 shell 测试套件）
- 测试脚本使用 GNU coreutils 长选项

## 根因分析

OHOS 的 `/bin` 使用 toybox 实现 coreutils，`stat` 只支持 `-c FORMAT`，
`cmp` 只支持 `-n LEN` 与位置参数 `SKIP1 SKIP2`，不接受 GNU 的
`--printf`、`--bytes`、`--ignore-initial` 长选项。上游测试在 glibc 发行版上通过，
在 OHOS 上直接报 unknown option。

另一个语义陷阱：GNU `cmp --ignore-initial=SKIP` 对**两个输入文件同时**跳过
`SKIP` 字节，而 `--ignore-initial=A:B` 才是分别指定；替换为位置参数时必须
写成 `cmp -n LEN FILE1 FILE2 A B`，否则比较区域错位。

## 解决方案

### 推荐方案

- `stat --printf="%s" FILE` → `stat -c %s FILE`
- `cmp --bytes=N FILE1 FILE2` → `cmp -n N FILE1 FILE2`
- `cmp --ignore-initial=A:B --bytes=N FILE1 FILE2` → `cmp -n N FILE1 FILE2 A B`
- `cmp --ignore-initial=A --bytes=N FILE1 FILE2` → `cmp -n N FILE1 FILE2 A A`

以上形式 GNU / toybox / BusyBox 均支持，可同时保留上游 Linux 兼容性。

### 禁止做法

- ❌ 不要直接删除这些比较断言（会削弱测试覆盖）。
- ❌ 不要把 `--ignore-initial` 的单值语义误写成只跳过第一个文件。

## 验证

```bash
/bin/stat -c %s /etc/hostname
/bin/cmp -n 4 file1 file2 0 0
make -C external/pflash check   # 02-erase/03-erase-parts/04-program-rand/05-bad-numbers
```

## 关联条目

- E2296（OHOS procfs readlink 截断，同属 pflash 测试适配）
