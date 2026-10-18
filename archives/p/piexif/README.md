# piexif

Exif manipulation library for Python — write, read and transplant Exif data
(pure Python, zero runtime dependencies).

## OpenHarmony 适配状态

- 支持版本: 1.1.3
- 构建系统: custom（纯 Python，无编译步骤）
- 运行时依赖: 无
- 测试依赖: pillow/10.4.0（`tool_requires`，仅构建期运行上游测试）

## 编译方法

```bash
python3 scripts/ohc-run.py build piexif 1.1.3
```

## 使用示例

```python
import piexif

exif = piexif.load("image.jpg")          # read Exif
exif_bytes = piexif.dump(exif)           # serialize
piexif.insert(exif_bytes, "in.jpg", "out.jpg")
piexif.remove("in.jpg", "clean.jpg")
```
