# Qt 5.15 的 `qlogging.h` 只前置声明 `QDebug`：老工程 `qDebug() <<` 流式输出未包含头即编译中断

> Draft: `DRAFT-XDRAWCHEM-1111-QDEBUG-INCOMPLETE-TYPE-QT515`
> Stem: `xdrawchem-1.11.1-qdebug-incomplete-type-qt515` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-XDRAWCHEM-1111-QDEBUG-INCOMPLETE-TYPE-QT515
- **严重度**: 2
- **类别**: qt5|portability|header-dependency|clang
- **触发工具**: clang|g++|qmake|cmake|conan
- **阶段**: build

## 错误特征

xdrawchem 1.11.1 首次 `conan create` 在 `http.cpp` 中断（10 处 error）：

```
xdrawchem/http.cpp:29:5: error: calling 'debug' with incomplete return type 'QDebug'
    qDebug() << "HTTP:" << url1;
    ^~~~~~~~
.../src/corelib/global/qlogging.h:126:12: note: 'debug' declared here
    QDebug debug() const;
.../src/corelib/global/qlogging.h:57:7: note: forward declaration of 'QDebug'
class QDebug;

xdrawchem/http.cpp:29:14: error: use of overloaded operator '<<' is ambiguous
        (with operand types 'QDebug' and 'const char[6]')
.../src/gui/painting/qcolor.h:57:21: note: candidate function
Q_GUI_EXPORT QDebug operator<<(QDebug, const QColor &);
```

## 根因

Qt 5.15 的 `qlogging.h` 里只写 `class QDebug;`，并在注释中明确要求：

```
In order to use the qDebug() stream, you must #include<QDebug>
```

（`qdebug.h` 反向包含 `qlogging.h`，不存在隐式回环。）老工程习惯靠"碰巧"经由
`QApplication` / `QWidget` 等头间接拿到 `qdebug.h`，自己并不写 `#include <QDebug>`。
`http.cpp` 的 include 集合只有 `QCoreApplication/QDialog/QFile/QNetworkAccessManager/
QNetworkReply/QNetworkRequest/QSslError/QStringList/QTimer/QUrl` + `<stdio.h>`——
**没有**任何头引入 `qdebug.h`，于是：

1. `qDebug()` 展开为 `QMessageLogger(...).debug()`，返回不完整类型 `QDebug` →
   `calling 'debug' with incomplete return type`；
2. `QDebug` 不完整时，重载解析只能看到由 `QColor/QMatrix/QTransform/QVariant` 隐式
   转换构造出来的 `operator<<` 候选 → `use of overloaded operator '<<' is ambiguous`。

显著特点：**同一工程其它 .cpp 大多没事**（它们的 include 集合恰好引进了 qdebug.h），
所以症状是"只有个别文件挂"，容易误判成源码语法问题。

## 修复

1. **先全量枚举**：用 `make -k -j1`（不要用 `make -jN` 首次失败即停）把全部失败
   TU 列出来。xdrawchem 中匹配 `qDebug()|qWarning()|qInfo()|qCritical()` 的 .cpp 共 **52** 个
   （若只按 `qDebug` 字样统计：48 个 .cpp、含头文件 54 个文件），实际失败 **1** 个。
2. 在受影响文件补 `#include <QDebug>`（补丁 `0002-xdrawchem-http.cpp.patch`，+2 行）。
3. **不要**用 `-include QDebug` 或定义 `qDebug` 宏来"一把过"——前者把源码头依赖
   挪进构建参数、换构建系统即丢；后者改变上游运行期诊断行为，属无关改动。

> 同类命中很多（>10 个 TU）时，才考虑统一放进工程公共头 / PCH，并在 PR 说明中标注。

## 验证

```bash
make -k -j1 2>&1 | grep -c "incomplete return type 'QDebug'"   # 期望 0
./bin/<app> --version                                          # 期望正常执行
```
