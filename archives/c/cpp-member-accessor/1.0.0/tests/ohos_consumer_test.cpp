// HarmonyOS 专项消费者端到端测试 — cpp-member-accessor 1.0.0
//
// 目的：赛事 Review 规则 12「鸿蒙特有测试」——在目标 OH 平台（aarch64,
// clang-15, libc++）上真实编译并运行一个**完整消费者端到端用例**，用
// cpp-member-accessor 的公共 API 对真实被测类型跑通成员访问/代理访问
// 流程闭环，并对库实际产生的可观察结果做断言（可失败，非恒绿）。
//
// 平台差异走标准库单一路径，不引入平台条件编译宏（R8）。
// 消费者必须使用 MakeProxy + accessMember/callFunction 习语
// （R01 知识判定：直接构造 Proxy 静态成员会段错误，禁止使用）。

#include <accessor/accessor.hpp>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>
#include <utility>

// ── 被测真实类型：含 private 成员变量与 private 成员函数 ──
class BankAccount {
public:
    BankAccount() = default;
    BankAccount(std::string name, double balance)
        : name_(std::move(name)), balance_(balance), txn_count_(0) {}

private:
    std::string name_;
    double balance_;
    int txn_count_;

    void applyFee(double fee) { balance_ -= fee; }
    bool isOverdrawn() const { return balance_ < 0.0; }
};

// ── MakeProxy 显式实例化：标准允许显式实例化忽略访问限定符 ──
// 注意：显式实例化必须位于 accessor 的外层全局作用域（不能放入匿名命名空间），
// 与上游 tests/ 的用法一致。
struct NameAccessor : accessor::MemberWrapper<BankAccount, std::string> {};
template class accessor::MakeProxy<NameAccessor, &BankAccount::name_>;

struct BalanceAccessor : accessor::MemberWrapper<BankAccount, double> {};
template class accessor::MakeProxy<BalanceAccessor, &BankAccount::balance_>;

struct TxnAccessor : accessor::MemberWrapper<BankAccount, int> {};
template class accessor::MakeProxy<TxnAccessor, &BankAccount::txn_count_>;

struct ApplyFeeFn : accessor::FunctionWrapper<BankAccount, void, double> {};
template class accessor::MakeProxy<ApplyFeeFn, &BankAccount::applyFee>;

struct IsOverdrawnFn : accessor::ConstFunctionWrapper<BankAccount, bool> {};
template class accessor::MakeProxy<IsOverdrawnFn, &BankAccount::isOverdrawn>;

int main()
{
    int failures = 0;

    // ── 闭环 1：多成员 set/get 往返（string / double / int）──
    {
        BankAccount acc("ohos-demo", 100.0);
        accessor::accessMember<NameAccessor>(acc).get() = "harmonyos-check";
        accessor::accessMember<BalanceAccessor>(acc).get() = 250.0;
        accessor::accessMember<TxnAccessor>(acc).get() = 7;

        const bool ok = (accessor::accessMember<NameAccessor>(acc).get() == "harmonyos-check")
                     && (accessor::accessMember<BalanceAccessor>(acc).get() == 250.0)
                     && (accessor::accessMember<TxnAccessor>(acc).get() == 7);
        std::cout << "[ohos-consumer] roundtrip set/get (name,balance,txn): "
                  << (ok ? "PASS" : "FAIL") << "\n";
        if (!ok) ++failures;
    }

    // ── 闭环 2：调用 private 成员函数并校验可观察结果 ──
    {
        BankAccount acc("fee-demo", 100.0);
        accessor::callFunction<ApplyFeeFn>(acc, 12.5);
        const double after = accessor::accessMember<BalanceAccessor>(acc).get();
        const bool ok = (std::abs(after - 87.5) < 1e-9);
        std::cout << "[ohos-consumer] callFunction(applyFee 12.5) -> balance "
                  << after << ": " << (ok ? "PASS" : "FAIL") << "\n";
        if (!ok) ++failures;
    }

    // ── 闭环 3：const 成员函数路径 ──
    {
        const BankAccount acc("overdrawn-demo", -30.0);
        const bool overdrawn = accessor::callFunction<IsOverdrawnFn>(acc);
        const bool ok = (overdrawn == true);
        std::cout << "[ohos-consumer] const callFunction(isOverdrawn) -> "
                  << (overdrawn ? "true" : "false") << ": "
                  << (ok ? "PASS" : "FAIL") << "\n";
        if (!ok) ++failures;
    }

    // ── 闭环 4：非 const 实例上的 const 函数 + 修改后状态往返 ──
    {
        BankAccount acc("state-demo", 50.0);
        const bool notOverdrawn = accessor::callFunction<IsOverdrawnFn>(acc);
        accessor::callFunction<ApplyFeeFn>(acc, 60.0);
        const double after = accessor::accessMember<BalanceAccessor>(acc).get();
        const bool overdrawn = accessor::callFunction<IsOverdrawnFn>(acc);
        const bool ok = (notOverdrawn == false) && (std::abs(after - (-10.0)) < 1e-9)
                     && (overdrawn == true);
        std::cout << "[ohos-consumer] state transition 50.0 -> " << after
                  << " (overdrawn " << (overdrawn ? "true" : "false") << "): "
                  << (ok ? "PASS" : "FAIL") << "\n";
        if (!ok) ++failures;
    }

    std::cout << "[ohos-consumer] RESULT: " << (failures == 0 ? "ALL PASS" : "FAILED")
              << " (failures=" << failures << ")\n";
    return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
