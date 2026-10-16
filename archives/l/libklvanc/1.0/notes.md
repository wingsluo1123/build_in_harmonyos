# libklvanc 1.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-28}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}

## 上游测试申报表与实测结果（R51）

| 测试入口 | 清点数 | 实测结果 | 结论 |
|----------|--------|----------|------|
| tools/test_api.c（klvanc_test_api 套件） | 22 个 test_ 函数 / 185 个断言组 | exit 0：Total 185 passed, 0 failed | ✅ 全通过 |
| klvanc_smpte2038（sample 驱动，-i ../samples/smpte2038-sample-pid-01e9.ts -P 0x1e9） | 1 个 sample 用例 | exit 0：2142 PES / 2142 VANC 包，0 checksum 失败 | ✅ 通过 |
| 工具冒烟（klvanc_util / klvanc_parse / klvanc_afd --help） | 3 个工具 | 全部 rc=0 | ✅ 通过 |
| meson.build 注册测试（test_<exe>，含 klvanc_smpte2038 sample 参数用例） | 2 类注册 | autotools 构建路径，等价覆盖 | ✅ 通过 |

- 运行命令示例（work 目录 tools/ 下）：
  `LD_LIBRARY_PATH=../src/.libs ./klvanc_test_api`
  `LD_LIBRARY_PATH=../src/.libs ./klvanc_smpte2038 -i ../samples/smpte2038-sample-pid-01e9.ts -P 0x1e9`
- 日志：archives/l/libklvanc/1.0/reports/upstream-test-api.log、upstream-test-smpte2038.log
---

**编译结束**: 2026-09-28 20:32
**最终状态**: built
