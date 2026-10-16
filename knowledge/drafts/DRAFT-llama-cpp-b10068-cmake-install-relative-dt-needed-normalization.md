# CMake install 的 bin/+lib/ 分离布局会烤出相对路径 DT_NEEDED（如 ../bin/libxxx.so）——包内自加载侥幸可用，消费者从其他目录加载必失败，打包期须遍历全部 ELF 归一为裸文件名

- **草稿 ID**: DRAFT-llama-cpp-b10068-cmake-install-relative-dt-needed-normalization
- **来源**: llama/cpp-b10068 HarmonyOS PC 适配（MateBook 真机验证暴露 → package() 三步链修复 → 消费者加载通过、W4 审计 PASS，MR !15476）
- **分类**: packaging / elf / runtime / cmake
- **状态**: 草稿（knowledge/drafts，kv+md 一一对应）

## 问题 / 错误签名

- `patchelf --print-needed` 检查包内产物，出现**带路径成分**的
  DT_NEEDED 条目（llama 实测 14 个 .so 中，8 个工具实现库 + libmtmd
  形如）：

```
NEEDED: ../bin/libggml-cpu.so      ← 工具在 bin/、依赖库在 lib/
```

- 加载失败现象随消费者位置浮动：包内目录结构不变时侥幸可用；
  conan 缓存复制、消费者从其他目录加载即
  `Error loading shared library ../bin/libxxx.so`。

## 根因

1. 上游 CMake 工程 bin/（可执行）与 lib/（库）分离安装时，构建树
   RPATH 经 install 转换，以**相对目标位置**的形式进入 DT_NEEDED；
2. musl loader 对带路径成分（绝对或相对）的 DT_NEEDED **不做常规
   搜索路径展开**——绝对条目按字面路径找（cvsgraph 条目），相对条目
   按加载者位置解析，包内容一经复制/重定位路径关系即破裂；
3. 与相邻条目划界：
   - **cvsgraph-1.7.0 草稿**：发布包烤**绝对**路径 NEEDED，根因=链接
     时把依赖 libdir 全路径写进 NEEDED（构建环境泄漏）；
   - **E330**：cmake_symlink_library 权限 + NEEDED 含 .conan2 缓存路径
     （链接期缓存路径泄漏）；
   - **本条**：**相对路径**，来源=install rpath 布局转换——三者共同
     本质都是"loader 对带路径 NEEDED 不做搜索"，但成因与修复位置不同。

## 影响面

- bin/+lib/ 分离安装的 CMake 项目、多 .so 工具型包（工具 + 各自实现库）；
- **重灾区是工具实现库**：修复只扫 lib/ 主库会漏掉 bin/ 可执行依赖的
  impl 库（llama 实测 8 个 impl 库全部带相对 NEEDED）；
- L5a 门禁要求所有 lib/*.so 有 SONAME，但对 **bin/ 下文件**的
  NEEDED 形态无门禁——此处是检查盲区，须配方自查。

## 最小处置方案

package() 内 cmake.install() 之后，三步固定顺序：

```python
# ① 补 DT_SONAME（L5a 门禁）
# ② 归一 DT_NEEDED：遍历包内全部 ELF（lib/*.so* + bin/ 全部文件）
#    patchelf --print-needed 读条目 → 含路径成分的逐条归一：
patchelf --replace-needed "../bin/libggml-cpu.so" libggml-cpu.so <file>
# ③ XPM 重签名（patchelf → llvm-objcopy 剥 .codesign → binary-sign-tool selfSign）
```

- **顺序不可换**：改 ELF（SONAME + NEEDED）必须全部在签名**之前**，
  签名后任何字节修改都使 XPM 签名失效；
- **不要**用 sed 直接改 ELF 字节（section 偏移损坏）；
- 归一前提：依赖同在本包 lib/ 内且已补 SONAME，裸文件名配合 loader
  常规搜索 + conan 的 LD_LIBRARY_PATH 注入即可解析；
- 遍历自动化实现参考 llama/cpp-b10068 配方 `_set_soname_and_resign`。

## 查重声明

撰写前对知识库 doc/graph/drafts 全量扫描比对（2026-10-12）：
**无同类条目**（"DT_NEEDED 相对路径归一"无命中）。相邻主题已逐一
核实并划界——cvsgraph-1.7.0-fontconfig-baked-abs-dt-needed（绝对路径，
发布包缓存路径泄漏，同族不同因）、DRAFT-libharu-2.3.0-missing-dt-soname
（缺 SONAME，不涉 NEEDED 形态）、E330（cmake symlink 权限 + 缓存路径
NEEDED）、E465（python dlsym，无关）。
