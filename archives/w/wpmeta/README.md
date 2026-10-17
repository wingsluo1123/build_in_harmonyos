# wpmeta

[wpmeta](https://github.com/AOSC-Dev/wpmeta) 是 AOSC（安同开源社区）的壁纸元数据
生成器：遍历由 `metadata.toml` 描述的壁纸源目录树，为 GNOME 与 KDE 生成可安装
的壁纸包元数据（`gnome-background-properties` XML 与 KDE `KPlugin`
`metadata.json`），将壁纸图像拷贝/规范化到目标目录结构，并通过 kmeans 调色板
（quantette）+ material-color-utilities 评分提取壁纸主色与强调色，可选生成
预览图（`contents/screenshot.jpg`）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.2.0 | built | 首次适配（上游 tag `wpmeta-v0.2.0`）；aarch64-unknown-linux-ohos，cargo --locked 构建，上游 10/10 单测通过 |

## 用法

```bash
WPMETA_LOG=info wpmeta --src <SRCDIR> --dst <PKGDIR> [--preview-resolution-limit 500,500]
```
