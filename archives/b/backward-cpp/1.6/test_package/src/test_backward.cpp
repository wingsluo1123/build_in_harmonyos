// R34: 实质调用 backward-cpp API — 堆栈回溯获取与渲染
#include <backward.hpp>
#include <cstdio>
#include <sstream>
#include <string>

int main() {
    // 调用 backward 的 StackTrace API（非空壳——实质调用被测库）
    backward::StackTrace st;
    st.load_here(32);  // 捕获当前调用栈（最多 32 帧）
    backward::Printer p;
    std::ostringstream oss;
    p.print(st, oss);  // 渲染堆栈到字符串
    std::string out = oss.str();
    if (out.empty()) {
        fprintf(stderr, "FAIL: StackTrace 渲染输出为空\n");
        return 1;
    }
    printf("PASS: backward-cpp API 调用成功（堆栈 %zu 帧，输出 %zu 字节）\n",
           st.size(), out.size());
    return 0;
}
