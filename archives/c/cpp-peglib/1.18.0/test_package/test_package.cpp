/*
 * test_package.cpp — cpp-peglib 1.18.0 消费者用例（10 项判据）
 *
 * 真消费交付的 `peglib.h`（CMakeDeps 的 cpp-peglib::cpp-peglib），只用上游
 * README/头文件里公开的 API：语法字符串构造 parser、`parse()` 的 bool/std::any
 * 两种形态、语义动作（SemanticValues + sv.token()/sv.str()）、`parser.log`
 * 错误回调。期望值全部是语法/输入的**字面量**，不拿库当自己的 oracle。
 *
 * 本机用 `-Wall -Wextra -std=c++17` 真编译真运行过（见 PR 描述）。
 */
#include <peglib.h>

#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>

static int checks = 0;
static int failures = 0;

static void chk(const std::string &what, bool ok, const std::string &got)
{
  ++checks;
  if (!ok)
    ++failures;
  std::cout << "  [" << (ok ? "ok" : "FAIL") << "] " << what << " (" << got
            << ")\n";
}

int main()
{
  /* 1/2 — 头文件版本契约（1.18.0 新增的宏，消费者可直接核对） */
  chk("CPPPEGLIB_VERSION == \"1.18.0\"", std::string(CPPPEGLIB_VERSION) == "1.18.0",
      CPPPEGLIB_VERSION);
  chk("CPPPEGLIB_VERSION_NUM == \"0x011200\"",
      std::string(CPPPEGLIB_VERSION_NUM) == "0x011200", CPPPEGLIB_VERSION_NUM);

  /* 3/4 — 最小字面量语法：合法输入接受、非法输入拒绝 */
  peg::parser literals(R"(
    Start <- 'hello'
  )");
  chk("字面量语法构造成功", static_cast<bool>(literals) == true,
      static_cast<bool>(literals) ? "parser ok" : "construction failed");
  chk("合法输入 'hello' 被接受", literals.parse("hello") == true,
      literals.parse("hello") ? "accepted" : "rejected");

  /* 5/6 — 语义动作 + 优先级/括号：真跑一个算术求值语法 */
  peg::parser calc(R"(
    EXPRESSION <- TERM ( <'+'> TERM )*
    TERM       <- FACTOR ( <'*'> FACTOR )*
    FACTOR     <- NUMBER / '(' EXPRESSION ')'
    NUMBER     <- < [0-9]+ >
    %whitespace <- [ \t]*
  )");
  long long acc = 0;
  calc["EXPRESSION"] = [&acc](const peg::SemanticValues &sv) -> long long {
    acc = std::any_cast<long long>(sv[0]);
    for (size_t i = 1; i < sv.size(); i += 2) {
      const auto op = sv.token(i - 1);
      const auto v = std::any_cast<long long>(sv[i]);
      acc = (op == "+") ? acc + v : acc - v;
    }
    /* 必须返回值：choice 1（括号分支）要拿 EXPRESSION 的语义值 */
    return acc;
  };
  calc["TERM"] = [](const peg::SemanticValues &sv) -> long long {
    long long v = std::any_cast<long long>(sv[0]);
    for (size_t i = 1; i < sv.size(); i += 2) {
      const auto op = sv.token(i - 1);
      const auto r = std::any_cast<long long>(sv[i]);
      v = (op == "*") ? v * r : v / r;
    }
    return v;
  };
  calc["FACTOR"] = [](const peg::SemanticValues &sv) -> long long {
    /* choice 0 = NUMBER；choice 1 = '(' EXPRESSION ')' —— 字面量不产生语义值，
       两条分支都只有一个 long long（本机 probe 实测 size=1） */
    return std::any_cast<long long>(sv[0]);
  };
  calc["NUMBER"] = [](const peg::SemanticValues &sv) -> long long {
    return std::stoll(sv.token_to_string());
  };

  if (!calc) {
    chk("算术语法构造成功（含 %whitespace 与 <token> 算子）", false,
        "grammar construction failed");
    return 1;
  }
  long long v1 = 0;
  const bool ok1 = calc.parse("1+2*3", v1);
  chk("算术语法求值 '1+2*3' == 7（动作 + 优先级）", ok1 && v1 == 7,
      "parsed=" + std::string(ok1 ? "true" : "false") + " value=" +
          std::to_string(v1));
  long long v2 = 0;
  const bool ok2 = calc.parse("(1+2)*3", v2);
  chk("算术语法求值 '(1+2)*3' == 9（括号优先级）", ok2 && v2 == 9,
      "parsed=" + std::string(ok2 ? "true" : "false") + " value=" +
          std::to_string(v2));

  /* 7 — token（% 前缀）算子：CSV 风格语法切出 3 项 */
  peg::parser csv(R"(
    LIST  <- ITEM (',' ITEM)*
    ITEM  <- < [a-z]+ >
  )");
  std::vector<std::string> items;
  csv["ITEM"] = [&items](const peg::SemanticValues &sv) {
    items.push_back(sv.token_to_string());
  };
  if (!csv) {
    chk("逗号分隔语法构造成功", false, "grammar construction failed");
    return 1;
  }
  const bool ok3 = csv.parse("alpha,beta,gamma");
  chk("带逗号分隔的语法切出 3 个 item", ok3 && items.size() == 3,
      "parsed=" + std::string(ok3 ? "true" : "false") + " items=" +
          std::to_string(items.size()));

  /* 8/9 — 错误回调：非法输入必须在**第一个字符**处报错并给出非空消息 */
  size_t err_line = 0, err_col = 0;
  std::string err_msg;
  peg::parser guarded(R"(
    Start <- 'hello'
  )");
  guarded.set_logger([&](size_t line, size_t col, const std::string &msg) {
    err_line = line;
    err_col = col;
    err_msg = msg;
  });
  const bool rejected = guarded.parse("world") == false;
  chk("非法输入 'world' 被拒绝", rejected, rejected ? "rejected" : "accepted");
  chk("错误定位为第 1 行第 1 列（不匹配发生在首字符）且消息非空",
      err_line == 1 && err_col == 1 && !err_msg.empty(),
      "line=" + std::to_string(err_line) + " col=" + std::to_string(err_col) +
          " msg=" + err_msg);

  /* 10 — parse(sv, val) 的语义值形态：'42' -> 42 */
  peg::parser num(R"(
    Start <- < [0-9]+ >
  )");
  long long parsed_value = 0;
  num["Start"] = [](const peg::SemanticValues &sv) -> long long {
    return std::stoll(sv.token_to_string());
  };
  const bool ok4 = num.parse("42", parsed_value);
  chk("parse(input, val) 取回语义值 42", ok4 && parsed_value == 42,
      "parsed=" + std::string(ok4 ? "true" : "false") + " value=" +
          std::to_string(parsed_value));

  std::cout << "consumer use case: " << checks << " checks, " << failures
            << " failure(s)\n";
  return failures == 0 ? 0 : 1;
}
