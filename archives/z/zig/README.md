# Zig

Zig is a general-purpose programming language and toolchain for maintaining
robust, optimal, and reusable software.

This archive provides Zig as a Conan build tool package so downstream recipes
can use:

```python
self.tool_requires("zig/0.16.0")
```

The package preserves the official Zig distribution layout inside `bin/`, so
the real `zig` executable and its required `lib/` directory remain siblings.
