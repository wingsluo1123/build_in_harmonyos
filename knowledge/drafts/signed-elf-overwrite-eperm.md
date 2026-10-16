# DRAFT: 已签 ELF 覆盖写 EPERM（HMDFS）

## 现象

对已签名的 ELF 文件做原位重写：

```python
open("/path/to/signed-elf", "wb").write(data)
# → PermissionError: [Errno 1] Operation not permitted
```

sed -i / shell 重定向同样被拒。

## 根因

HMDFS 对含 `.codesign` 段的文件实施完整性保护，原位截断/重写一律
EPERM（errno 1），与权限位无关，chmod 不能绕过。

## 修复（临时文件 + 原子替换）

```python
# python
tmp = p + ".new"
open(tmp, "wb").write(data)
os.remove(p)          # 先删原件
os.rename(tmp, p)     # 原子替换（HMDFS 支持 rename）
os.chmod(p, 0o755)
```

```sh
# shell
cp f f.ws
llvm-objcopy --remove-section .codesign f.ws
binary-sign-tool sign -inFile f.ws -outFile f.ws -selfSign 1
rm -f f && mv f.ws f
```

## 注意

- 写入即破坏原 `.codesign`，替换后**必须重签**并双验
  （`llvm-readelf -S | grep codesign` + 实际运行）；
- `open(p, "wb")` 在截断阶段即触发 EPERM，连写都没写进去；
- 签名工具自身的 inFile→outFile（不同路径）不受影响。

## 实证

php-8.5.8 制品二进制 patch（conan 路径清理 + ini 默认值指针重定向）：
直写 EPERM → 临时文件 + rm/mv 替换成功（2026-10）。
