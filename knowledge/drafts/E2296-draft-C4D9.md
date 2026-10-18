# E2296 — Bison 3.8 把内建 error token 纳入 `<prefix>error` 枚举，与 yyerror 回调同名冲突

## 错误特征

```
error: redefinition of 'AST_error' as different kind of symbol
error: called object type 'AST_tokentype' is not a function or function pointer
```

日志中同时出现：语法文件 prologue 里定义的回调名（如 `AST_error`/`Schema_error`）
与生成头文件中的 `enum AST_tokentype { AST_error = 256, ... }` 冲突。

## 触发条件

- 构建系统: bison（CMake/Autotools 均可触发）
- 上游使用 `%define api.prefix {AST_}` 且自定义了同名错误回调
- Bison >= 3.8（内建 `error` token 也开始套用 api.prefix）

## 根因分析

Bison 3.8 起将内建 `error` token 也按 `api.prefix` 命名并放入 token-kind 枚举。
上游代码习惯把错误回调命名为 `<Prefix>error`，与枚举成员同名；C++ 不允许
同一作用域内枚举成员与函数同名，因此编译失败。

## 解决方案

### 推荐方案

在语法文件的 `%{ ... %}` prologue 中重定向 `yyerror`，回调改用独立名字：

```c
    #undef yyerror
    #define yyerror AST_error_handler
    void AST_error_handler ( ctx_t ctx, ... )
```

回调实现保持不变；`yyerror` 宏由 bison 在 prologue 之前生成，`#undef` 后可安全重定向。

### 禁止做法

- ❌ 修改生成文件 `zz_*.cpp/.hpp`（下次构建会被覆盖）
- ❌ 把回调改名但仍让 bison 生成同名 token（如继续使用 `api.token.prefix` 冲突名）

## 验证

```bash
bison --version | head -1
grep -n 'error_handler' libs/schema/schema-ast.y libs/schema/schema-grammar.y
# 重新编译，确认 redefinition / not a function 错误消失
```

## 关联条目

- 相关: E092（CMake 平台识别）
