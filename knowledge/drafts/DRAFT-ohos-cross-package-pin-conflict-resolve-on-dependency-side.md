# DRAFT-ohos-cross-package-pin-conflict-resolve-on-dependency-side

> 维护者复审候选草稿（Path B 知识扩展材料）；**不自动作为 Path B 评级或分值依据**。

## 现象

消费者要同时用两条已发布依赖链时，图直接冲突（本轮：mplayer 想启用 gmplayer GUI，需 gtk2；而字幕栈 libass 已在图内）：

```
ERROR: Version conflict: Conflict between harfbuzz/14.2.0 and harfbuzz/14.2.0.1.1.1 in the graph.
ERROR: Version conflict: Conflict between libjpeg-turbo/3.2.0 and libjpeg-turbo/3.0.4 in the graph.
```

两侧钉版：

| 链 | 钉版 |
|---|---|
| 字幕：`libass/0.17.5` | `harfbuzz/14.2.0` |
| GUI：`gtk2/2.24.33` → `pango/1.50.14.1.1` | `harfbuzz/14.2.0.1.1.1` |
| 图像：`libmng/2.0.3` | `libjpeg-turbo/3.0.4` |
| GUI：`gtk2` → `gdk-pixbuf/2.44.6.1.1` | `libjpeg-turbo/3.2.0` |

## 为什么不用 override / force

- **`override=True`**：能强行统一，但会迫使 `libass`/`libmng` 这类**已发布**依赖在 CI 里从源码重建
  （违反仓内 R36 依赖已发布原则；且 libass 的源就在 GitHub，本环境不可达，重建还得先解决换源）。
- **`force=True`**：只在**本配方参与解析的图**里改写版本，消费者图仍按各自钉版解析 →
  表现为“本包能过、消费者图硬冲突”（本轮 `samba/4.21.0` 的 `zlib/1.3.1, force=True` 即如此；
  正解是 `samba/4.21.0.1` 递增并把钉版对齐 `zlib/1.3.1.1`）。

## 推荐处置：依赖侧“只改钉版”的递增版本

本轮落地为一条三件套链（各自独立 PR）：

| 包 | 版本 | 改动 |
|---|---|---|
| `pango` | 1.50.14.1.1 → **1.50.14.1.1.2** | `harfbuzz/14.2.0.1.1.1` → **14.2.0**（对齐 libass）；`test_package` 内钉版一并同步 |
| `gdk-pixbuf` | 2.44.6.1.1 → **2.44.6.1.1.1** | `libjpeg-turbo/3.2.0` → **3.0.4**（对齐 libmng） |
| `gtk2` | 2.24.33 → **2.24.33.1** | 要求上面两个新版本；其余依赖/源/补丁/选项不变 |

要点：
1. **先查有没有已发布的第三版本**能同时满足（零重建最省）——本轮两边都只有各自线，故走递增。
2. 递增版本**只改钉版**：源、补丁、configure 选项、产物布局保持不变，便于复审与最小化差异。
3. **`test_package` 里的显式钉版必须同步**：否则测试包自身会图冲突（pango 本轮实测：
   `ERROR: Version conflict: Conflict between harfbuzz/14.2.0 and harfbuzz/14.2.0.1.1.1 in the graph`，
   修法是同步测试包钉版）。
4. 逐件独立 PR（W2 原子性），PR 正文写清“不 override / 不 force”的理由与两侧钉版证据。

## 验证

```
# 三件套依次构建（全部 rc=0，消费者测试各自的实测输出见对应 PR）
conan create archives/p/pango/1.50.14.1.1.2      # pango ok version=1.50.14 (pangocairo)
conan create archives/g/gdk-pixbuf/2.44.6.1.1.1  # gdk-pixbuf 2.44.6.1.1 OK: 16x16 channels=4 has_alpha=1
conan create archives/g/gtk2/2.24.33.1           # gtk2 2.24.33 consumer check ok
# 目标态整图（mplayer + gtk2 链 + live555 + cddb + dga + samba）无 Version conflict
```

## 证据

- `archives/p/pango/1.50.14.1.1.2/reports/pr-body.md`（含 test_package 钉版同步的踩坑）
- `archives/g/gdk-pixbuf/2.44.6.1.1.1/reports/pr-body.md`
- `archives/g/gtk2/2.24.33.1/reports/pr-body.md`（含 `gtk2/2.24.33.1` 同时修构建期 libintl 的两族符号互斥）
- `archives/s/samba/4.21.0.1/notes.md`（force 的跨图副作用与递增对齐）
