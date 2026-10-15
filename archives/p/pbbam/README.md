# pbbam

## 简介
PacBio BAM C++ 库，用于创建、查询和编辑 PacBio 兼容的 BAM 文件及相关索引（.pbi），是 PacBio HiFi 数据分析的基础库。

## OHOS 适配
- Meson 构建系统，OHOS 上关闭 tools/docs，只交付 libpbbam 纯库
- 依赖 Conan 制品仓的 boost/zlib/htslib；pbcopper 暂无 OHOS 配方，走上游 wrap 回退编译
- 上游 `meson test` 注册 3 个测试，配方在 build() 中完整运行并解析 testlog

## 依赖
- boost/1.85.0（全量头文件，含 numeric/ublas）
- zlib/1.3.1
- htslib/1.24-r0
- pbcopper（上游 wrap 回退，随构建编译）

## 功能验证
```bash
conan create archives/p/pbbam/2.4.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考
- 上游仓库: https://github.com/PacificBiosciences/pbbam
- 上游版本: v2.4.0
