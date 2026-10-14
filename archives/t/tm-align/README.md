# tm-align

TM-align / TM-score（Zhang Lab，密歇根大学）：蛋白质结构比对与评分命令行工具。

- `TMalign`：序列无关的蛋白质单体结构比对，输出 TM-score、RMSD、旋转矩阵与比对序列
- `TMscore`：给定残基对应关系下的结构相似度评分（TM-score / MaxSub / GDT-TS / GDT-HA）

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 20190822 | built | Debian orig 包（`+dfsg`），仅构建 C++ 实现（`*.cpp`），不引入 gfortran，HarmonyOS PC (aarch64) 适配 |

## 构建

```bash
conan create . --version=20190822 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

产物：`bin/TMalign`、`bin/TMscore`。

## 依赖

仅 C++ 标准库与数学库（`-lm`），无 Conan 依赖。

## 适配说明

见 [20190822/notes.md](20190822/notes.md)。
