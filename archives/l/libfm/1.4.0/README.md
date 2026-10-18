# libfm-extra 1.4.0 — HarmonyOS PC 适配

仅构建 libfm-extra 子库（FmXmlFile 解析器），跳过完整 libfm/libfm-gtk。

## 依赖

- glib/2.88.0（已验证可消费）

## 构建

```bash
conan create archives/l/libfm/1.4.0
```

## 产物

- `lib/libfm-extra.so.4.1.3`（共享库）
- `include/libfm-4/{fm-extra.h, fm-xml-file.h, fm-version.h}`
- `lib/pkgconfig/libfm-extra.pc`

## 测试

test_package 包含 4 个消费者测试用例：
- XML 往返解析与序列化
- 属性提取
- 错误处理
- OHOS 运行时可用性（GType + 实例化）
