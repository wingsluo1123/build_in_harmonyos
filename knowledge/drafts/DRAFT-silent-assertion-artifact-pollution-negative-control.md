# DRAFT — 产物断言必须做负对照：无关内容（窗口装饰/固定 UI）会让断言永不失改

> 拟提升编号：E559（最终编号由知识库主编确认）
> 来源：termshot 0.6.1 消费者测试（2026-10-13，鸿蒙 PC 真机）

## 错误特征

```
PASS: screenshot created (11450 bytes)
PASS: valid PNG, 548x345 pixels
PASS: 1154 dominant-red pixels rendered (ANSI colour survived)   ← 看似通过
```

但这个断言**永不失改**：即使被检测命令完全没有输出 ANSI 颜色，结果仍然 PASS。

## 根因：artifact 里的混淆因素

termshot 消费者测试要验证"ANSI 颜色被终端仿真管线真实渲染"，做法是统计截图中
的 dominant-red 像素。但 termshot **默认绘制窗口装饰按钮**：

| 元素 | 颜色 |
|------|------|
| 窗口装饰按钮 | `#ED655A` = (237,101,90) |

代入判定式 `r>=120 且 r-g>=60 且 r-b>=60`：

```
r-g = 237-101 = 136 ≥ 60 ✓
r-b = 237-90  = 147 ≥ 60 ✓
```

**必然成立** → 与"颜色渲染功能是否正常"完全脱钩。

> 注：上游 `internal/cmd/root.go:116` 的 `--no-decoration` 正是为此提供的开关，
> `DrawDecorations(false)` 后不绘制按钮。

## 另一个方向的陷阱：算法错位

同一断言还踩过反向的坑——按 **3 字节步长**在**未解 filter** 的 IDAT 流上采样：

- PNG 每行首字节是 **filter type**
- gg / `image.RGBA` 输出是 **4 通道**（R,G,B,A）
- 不解 filter、按 3 字节跨 scanline 采样 → 什么都采不中，断言恒失败

两种毛病（恒通过 / 恒失败）本质相同：**断言与真实能力脱钩**。

## 解决方案

### 1. 消除混淆因素

```bash
termshot --no-decoration -f out.png -- /bin/sh -c 'printf "\033[31mRED\033[0m\n"'
```

### 2. 按 PNG 真实格式统计

```python
def _count_red_pixels(path):
    # 解析 IHDR + 合并多段 IDAT + zlib 解压
    ...
    stride = width * channels          # 4 通道（RGBA）
    raw = zlib.decompress(idat)
    prev = bytearray(stride)
    pos = 0
    for _y in range(height):
        ftype = raw[pos]; pos += 1      # ⭐ 每行首字节是 filter type
        line = bytearray(raw[pos:pos + stride]); pos += stride
        if   ftype == 1:  ...  # Sub
        elif ftype == 2:  ...  # Up
        elif ftype == 3:  ...  # Average
        elif ftype == 4:  ...  # Paeth
        for x in range(width):
            r, g, b = line[x*channels], line[x*channels+1], line[x*channels+2]
            if r >= 120 and r-g >= 60 and r-b >= 60:
                red += 1
        prev = line
    return red
```

### 3. 负对照实证（关键）

| 组 | 命令 | 红色像素 | 断言结果 |
|----|------|---------|---------|
| 负对照 | `--no-decoration` + 无颜色 `echo` | **0** | 失败 ✓ |
| 正对照 | `--no-decoration` + `printf "\033[31mRED\033[0m\n"` | **1154** | 通过 ✓ |

两者结果不同 → 断言有区分力，是真断言。把这两个数字写进
`test_package/MANIFEST.yml` 与 `notes.md` 作为证据。

## 验证

```bash
# W3 实证（termshot 0.6.1）
conan create archives/t/termshot/0.6.1 -pr:h=... -pr:b=...   # EXIT=0
  PASS: 1154 dominant-red pixels rendered (ANSI colour survived)
```

## 推广价值

适用于**所有对产物做内容断言**的测试——只要 artifact 里可能存在与
被测能力无关的固有内容，就必须做负对照：

| 场景 | 混淆因素 | 处理 |
|------|---------|------|
| 截图 / 渲染图 | 窗口装饰、水印、logo | 关掉装饰 / 限定内容区 |
| 日志断言 | 固定 banner、表头 | 只断言变化部分 |
| 二进制断言 | 固定字符串、build-id | 排除静态段 |
| CLI 输出 | 版本行、usage | 过滤固定行 |

核心原则：**"出现某特征即通过"必须证明该特征不可能由其他因素产生**——
最直接的证明方法就是让被测能力不生效，看断言是否失败。
