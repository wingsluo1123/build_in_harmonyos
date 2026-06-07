# Tmux Terminal Multiplexer

> Terminal multiplexer for managing multiple terminal sessions

## 简介

Tmux is a terminal multiplexer that lets you create, access, and control multiple terminals from a single screen. It enables:
- Split terminal windows into panes
- Detach and reattach sessions
- Persist terminal sessions across SSH connections

## OHOS 适配要点

1. Requires ncurses for terminal handling
2. Single binary tool with no shared libraries

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.5 | Terminal handling |

## 功能验证

```bash
tmux -V
tmux new-session -s test
```

## 参考

- [官方文档](https://github.com/tmux/tmux/wiki)
