# perl-readonly 2.05.1

基于官方 Readonly 2.05 的 HarmonyOS PC 原生适配修订版，提供标量、数组和深层哈希的只读约束。原始分发的唯一模块 Readonly.pm 按官方 SHA256 原样安装；适配修订号与上游版本分别记录。

## 构建与原始测试

采用已发布 Perl 5.42.2。分发资产仅一个纯 Perl 模块，无 XS 或生成代码；Conan 直接按资产清单安装，并由同一目标 Perl 的 Test::Harness 运行全部递归原始14个程序。保留188条断言清单，171条适用断言通过；17条上游原始互斥守卫已获确认不适用，逐文件逐编号与理由固定，任何额外SKIP、TODO或失败都拒绝。

```sh
conan create archives/p/perl-readonly/2.05.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never
```

## 安装后验证

消费者3项：现代Perl内置标量只读、Readonly::Array限定函数依赖及真正缺失的Readonly/Array.pm对照、嵌套哈希约束。Harmony专项1项：实际HarmonyOS aarch64、应用进程所有的0700私有POSIX目录、只读路径引用和真实UTF8二进制文件往返。

## 环境适配

路径列表首先使用 Environment.define_path，再追加源模块路径，保留真实核心和架构库目录。原始模块、测试文件和守卫保持官方字节；不修改发布的Perl、系统目录或权限。单次原生Conan create已独立审计，正式W3、平台CI和Review分别记录。
