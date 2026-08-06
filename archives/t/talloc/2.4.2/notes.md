# Notes — talloc 2.4.2

## 基本信息
- 软件名: talloc
- 版本: 2.4.2
- 构建系统: waf
- 状态: built

## 编译步骤
1. `./configure --prefix=/usr/local --disable-python CC=clang CXX=clang++`
2. `make -j2`
3. `make install`
4. `make check` (C testsuite passed, Python test skipped due to --disable-python)

## 补丁
- `0001-lib-replace-wscript.patch`: 修改 `lib/replace/wscript` 中 `HAVE_SECURE_MKSTEMP` 检查从 `mandatory=True` 改为 `mandatory=False`
  - 原因: OHOS 平台 `/tmp` 目录只读，`mkstemp` 检查失败导致 configure 中断
  - 回退方案: `replace.c` 中的 `rep_mkstemp()` 提供安全替代实现

## 依赖
无外部依赖。talloc 是独立的内存分配库。

## 验证命令和结果
```bash
# conan create 验证
conan create archives/t/talloc/2.4.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# G1-G4 全部通过，L2/L4/L5 通过

# 本地 CI 模拟
bash ci/conan/setup.sh && bash ci/conan/build_and_test.sh talloc/2.4.2
# 通过
```

## OHOS 适配注意事项
- talloc 使用 Samba 的 waf 构建系统，非标准 autotools
- `--disable-python` 必须添加，OHOS 不支持 Python 嵌入
- conanfile.py 使用 AutotoolsToolchain 但过滤掉 `${}` 模板参数和 shared/static 参数
- PYTHON 环境变量需设置为 python3 完整路径
