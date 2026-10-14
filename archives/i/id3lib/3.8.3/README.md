# id3lib 3.8.3（HarmonyOS PC 适配）

- 上游源码: id3lib-3.8.3.tar.gz（SourceForge 官方下载源）
- sha256: `2749cc3c0cd7280b299518b1ddf5a5bcfe2d1100614519b68702230e26c7d079`
- 构建系统: autotools（configure + make，autoconf 2.13 时代生成脚本）
- 目标平台: aarch64 HarmonyOS PC（os=OHOS，clang 15 / libc++，原生编译）

## 产物

- `lib/libid3.a` — 静态库
- `bin/id3info`、`bin/id3tag`、`bin/id3convert`、`bin/id3cp` — 命令行工具
- `include/id3.h`、`include/id3/*.h` — 头文件

## 使用（Conan）

```python
self.requires("id3lib/3.8.3")
```

```cpp
#include <id3/tag.h>

int main() {
  ID3_Tag tag("song.mp3");
  tag.AddFrame(ID3_Frame(ID3FID_LEADARTIST));
  tag.Update();
  return 0;
}
```

命令行工具安装后可直接使用：

```bash
id3info song.mp3
id3tag --artist="A" --song="B" song.mp3
```

## 上游测试

id3lib 无正式测试套件：`examples/` 下为演示/临时程序，`make check` 只编译
`check_PROGRAMS`（9 个），不执行任何测试。适配验证与实跑证据见
`reports/test-report.md`。
