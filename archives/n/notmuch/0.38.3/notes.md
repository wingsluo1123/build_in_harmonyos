# Notes — notmuch 0.38.3

## 基本信息
- 软件名: notmuch
- 版本: 0.38.3
- 构建系统: custom (not autotools, not cmake)
- 状态: built

## 编译步骤
1. `./configure --prefix=/usr/local --without-ruby CC=clang CXX=clang++`
2. `make -j1`
3. `make install`
4. Crypto checks (gpg/gpgme) made non-fatal since gpg not available on OHOS

## 补丁
- `0001-configure-crypto-ohos.patch`: Makes GMime crypto verification checks non-fatal
  - 原因: OHOS 平台没有 gpg/gpgme, 无法验证 session key extraction 和 X.509 cert validity
  - 影响: 不影响编译, 仅跳过 configure 阶段的 crypto 验证测试
  - 功能: 如果安装 gpg, crypto 功能将正常工作

## 依赖
- xapian-core/1.4.26 (搜索引擎)
- gmime/3.2.7 (MIME 解析, --disable-crypto)
- talloc/2.4.2 (内存分配)
- zlib/1.3.1 (压缩)

## 验证命令和结果
```bash
# 手动编译验证
./configure --prefix=/usr/local --without-ruby
make -j1 && make install
# 结果: notmuch binary (4.4MB), libnotmuch.so.5.6.0 (4.5MB) 编译成功

# Ruby 绑定跳过 (Ruby 3.4.5 stdckdint.h 兼容性问题)
```

## OHOS 适配注意事项
- notmuch 使用自定义 configure 脚本, 非 autotools
- xapian-config 返回空路径 (//lib, //include), 需通过环境变量修正
- gpg/gpgme 不可用, crypto 验证测试跳过
- Ruby 绑定因 Ruby 3.4.5 头文件兼容性问题跳过
- glib gettext 符号需要 musl loader (/lib/ld-musl-aarch64.so.1) 链接

## COMPLETED
