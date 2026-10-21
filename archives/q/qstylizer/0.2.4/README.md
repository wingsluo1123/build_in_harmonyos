# qstylizer 0.2.4

用于生成和解析 Qt 样式表的纯 Python 库。来源、固定依赖、修复及执行边界见 [notes.md](notes.md)。

```python
from qstylizer.parser import parse
css = parse('QLabel { qproperty-text: "left;right"; color: red; }')
css.QLabel.color.setValue('blue;')
assert css.QLabel['qproperty-text'].value == '"left;right"'
print(css.toString())
```

输出中的属性文本仍为 `"left;right"`，颜色为 `blue`；属性的声明终止分号由输出器添加。本次只验证文本 API，不启动 Qt 或证明渲染效果。

测试：构建期保留上游 `test/` 全部 72 项和原 conftest.py；额外回归 7 项；test_package 在独立进程中从交付包执行一次解析、修改、序列化和再解析流程（8 断言）。目标验证结果见 [test-report.md](test-report.md)。
