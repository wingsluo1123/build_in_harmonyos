# ncurses 6.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: published

## 编译步骤

关键配置参数如下：

```bash
./configure \
  --enable-static \
  --without-shared \
  --without-debug \
  --without-ada \
  --without-manpages \
  --without-tests \
  --without-cxx-binding \
  --enable-widec \
  --enable-overwrite \
  --enable-pc-files
make -j1
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conandata.yml` 中源码 `sha256` 为空 | 版本目录只有占位模板，未补全真实校验值 | 按 CI 已下载源码计算结果补全 `136d91bc269a9a5785e5f9e980bc76ab57428f604ce3e5a5a90cebc767971cc6` |
| 2 | GNU config 默认不识别 HarmonyOS 三元组 | `config.guess/config.sub` 缺少 `ohos` 分支 | 新增 `0001-port-for-ohos.patch`，补充 HarmonyOS 检测与 `linux-ohos` 合法性 |
| 3 | 消费者若继续链接 `-lncurses` 或额外假设存在 `-ltinfo` 会失败 | OHOS 上推荐使用 wide-char 静态库，当前产物只有 `libncursesw.a` | 在 recipe 中统一导出 `ncursesw`，下游按包信息链接 |

## 源码修改

- `patches/0001-port-for-ohos.patch`
  - 为 `config.guess` 添加 HarmonyOS 识别逻辑
  - 为 `config.sub` 添加 `ohos*` 与 `linux-ohos*` 支持

## 验证结果

```bash
python3 -m py_compile conanfile.py test_package/conanfile.py
```

## 注意事项

- 该版本沿用仓库内 `ncurses 6.4` 的鸿蒙适配结论，只产出静态宽字符库，避免共享库污染系统运行环境。
