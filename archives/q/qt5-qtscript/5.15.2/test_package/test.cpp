#include <QCoreApplication>
#include <QtScript/QScriptEngine>
#include <QtScript/QScriptValue>
#include <cstdio>

int main(int argc, char *argv[]) {
    QCoreApplication app(argc, argv);

    // 真实调用 Qt5Script API：创建脚本引擎并执行一段 JS 表达式
    QScriptEngine engine;
    QScriptValue result = engine.evaluate("1 + 1");
    if (result.isError()) {
        std::printf("Qt5Script test FAILED: %s\n",
                    result.toString().toUtf8().constData());
        return 1;
    }
    if (!result.isNumber()) {
        std::printf("Qt5Script test FAILED: eval(\"1+1\") is not a number\n");
        return 2;
    }
    // 往返断言：JS 表达式求值结果必须精确等于 2
    const double expected = 2.0;
    if (result.toNumber() != expected) {
        std::printf("Qt5Script test FAILED: eval(\"1+1\") = %f, expected %f\n",
                    result.toNumber(), expected);
        return 3;
    }

    // 二次往返：字符串/函数调用路径，验证引擎非浅层可用
    engine.globalObject().setProperty("x", 20);
    QScriptValue r2 = engine.evaluate("x + 22");
    if (r2.toNumber() != 42.0) {
        std::printf("Qt5Script test FAILED: eval(\"x+22\") = %f, expected 42\n",
                    r2.toNumber());
        return 4;
    }

    std::printf("Qt5Script test PASSED: eval(\"1+1\") == 2, eval(\"x+22\") == 42\n");
    return 0;
}
