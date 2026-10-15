# par_shapes

## 软件描述
par_shapes 是 prideout/par 单文件库集合中的三角网格库：生成、变换、合并 3D 三角网格并导出
Wavefront OBJ。全部功能在一个头文件（`par_shapes.h`）内——头文件即库，实现段由消费者
以 `PAR_SHAPES_IMPLEMENTATION` 编译。

Upstream: https://github.com/prideout/par

## 功能概述
- **形状生成**：立方体等五种正多面体、参数化圆柱/圆锥/球/平面/圆环/Klein 瓶/三叶结、
  细分球、可定向圆盘、噪声岩石、L-system 树
- **网格操作**：合并（可接管 source 所有权）、克隆（复用目标网格）、平移/旋转/缩放、翻转
- **属性**：参数化形状自动生成纹理坐标与焊接法线；细分球提供单位法线
- **导出**：OBJ（按属性组合输出 `v`/`vt`/`vn`/`f` 及其组合形态）

## OHOS 适配

### 构建方式
- **header-only**：无构建系统——`package()` 只安装 `include/par_shapes.h`
- 消费方式：单个翻译单元 `#define PAR_SHAPES_IMPLEMENTATION` 后 include 头文件

### 关键攻坚点
1. **卡面 URL 失效**：`anael-seghezzi/par_shapes` 已 404；canonical 上游为 prideout/par
   monorepo，无 tag，以 commit `68e1215a055ccbeae378dd5969e09d0c79963a4a` 钉定
2. **上游测试集成（R51）**：`build()` 内按上游 `test_shapes` 目标编译方式复刻并实跑
   `test/test_shapes.c`（16 用例，实测 16/16 通过）；导出用例写相对路径 `build/*.obj`
   共 15 个 OBJ 文件，运行目录预建 `build/`（导出函数不判 `fopen` 空，缺目录即段错误）
3. **E017 死域规避**：conandata 注释显式提及 ghfast.top 使真机注入守卫跳过，
   真机直连 `github.com` 下载 12.8MB 成功（日志无注入记录）

### 与 Linux 的差异
- 无差异——纯头文件库，全平台行为一致；OHOS 上 ELF 测试二进制经 `bash -c` 包装执行

## 依赖关系
无外部依赖（header-only；测试与消费者链接 libm，属标准 C 库）。

## 版本记录
| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| master | built | 2026-10-15 | 首次适配：header-only 打包 + 上游 16 用例实跑 + 消费者端到端执行器（12 用例/66 校验点）；真机八门禁 Verdict PASS |

## 目录

```
par_shapes/
├── manifest.yaml          # 软件级元信息与适配要点
├── README.md
└── master/
    ├── conanfile.py       # 主配方：header-only 打包 + build() 内实跑上游测试
    ├── conandata.yml      # 官方源（commit 钉定）+ sha256 + E017 免疫注释
    ├── manifest.yaml      # 版本级编译元数据
    ├── notes.md           # 本版适配笔记
    ├── reports/           # 真机 conan create 日志与八门禁报告
    └── test_package/      # Conan L1 消费者测试（12 用例端到端执行器）
```

## 参考资料
- 上游仓库: https://github.com/prideout/par
- 单文件库说明: par_shapes.h 头部注释（形状示例与 API 文档）
