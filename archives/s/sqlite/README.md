# SQLite Database

> Self-contained, serverless SQL database engine

## 简介
SQLite is a self-contained, high-reliability, embedded SQL database engine. It provides:
- `sqlite3`: Command-line database tool
- `libsqlite3`: Database library

## OHOS 适配要点
1. Fully self-contained, minimal dependencies
2. Works well on HarmonyOS

## 功能验证
```bash
sqlite3 --version
sqlite3 test.db "SELECT 1;"
```
