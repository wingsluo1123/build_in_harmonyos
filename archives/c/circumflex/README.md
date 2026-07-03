# circumflex

终端版 Hacker News 浏览器，支持 Vim 风格导航、语法高亮、Reader Mode。

- **官网**: https://github.com/bensadeh/circumflex
- **源码**: https://github.com/bensadeh/circumflex
- **许可证**: MIT
- **构建系统**: Go
- **分类**: CLI 工具 / 新闻阅读器

## 功能概述

- 📰 浏览 Hacker News 首页、最新、最佳、问答等分类
- 📖 Reader Mode 阅读文章全文
- 💬 查看评论，支持语法高亮
- ⌨️ Vim 风格快捷键导航
- 🔍 搜索文章和评论
- ⭐ 收藏喜欢的文章
- 🎨 多种主题支持

## OHOS 适配

### 关键适配要点

- **纯 Go 项目**: 无 CGO 依赖，使用 `CGO_ENABLED=0` 静态编译
- **体积优化**: `-ldflags="-s -w"` 去除符号表，最终体积约 19.6MB
- **TMPDIR**: 鸿蒙 `/tmp` 只读 (E002)，需设置 `TMPDIR` 到可写目录
- **GOPROXY**: 使用 `goproxy.cn` 加速依赖下载

### 已知问题

- 无（纯 Go 项目在鸿蒙上运行良好）

## 依赖关系

- **编译依赖**: Go 1.26+
- **运行依赖**: 无（静态编译，所有依赖已打包）

## 使用方法

```bash
# 启动交互式浏览
clx

# 查看版本
clx version

# 查看帮助
clx help
```

## 参考资料

- [GitHub 仓库](https://github.com/bensadeh/circumflex)
- [README](https://github.com/bensadeh/circumflex#readme)
- [快捷键说明](https://github.com/bensadeh/circumflex#keyboard-shortcuts)
