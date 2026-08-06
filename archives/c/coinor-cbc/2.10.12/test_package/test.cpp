/* Cbc 2.10.12 真实功能断言。
 *
 * Cbc 是分支定界 MIP 求解器。要验它真的**跑了分支定界**、而不只是把 LP 松弛
 * 原样返回，最干净的办法是挑一个「整数最优 ≠ LP 松弛最优」的问题：
 *
 *   max 5x + 4y   （内部按 min -5x -4y）
 *   s.t. 6x + 4y <= 24
 *         x + 2y <=  6
 *        x, y >= 0 且为整数
 *
 *   LP 松弛最优：(3, 1.5)  目标 21     ← 分数
 *   整数最优    ：(4, 0)    目标 20     ← 唯一
 *
 * 枚举可行整点核对唯一性：(4,0)=20、(3,1)=19、(2,2)=18、(1,2)=13、(0,3)=12。
 * 所以断言 20 且解为 (4,0) 是紧的：
 *   · 若求解器直接吐松弛解，目标会是 21 → 失败
 *   · 若它取整取错了顶点，解不会是 (4,0) → 失败
 */
#include "CbcModel.hpp"
#include "OsiClpSolverInterface.hpp"

#include <cmath>
#include <cstdio>

int main(void)
{
    OsiClpSolverInterface solver;
    solver.messageHandler()->setLogLevel(0);

    const int    ncol = 2, nrow = 2;
    const CoinBigIndex start[] = {0, 2, 4};
    const int          index[] = {0, 1, 0, 1};
    const double       value[] = {6.0, 1.0, 4.0, 2.0};
    const double       collb[] = {0.0, 0.0};
    const double       colub[] = {COIN_DBL_MAX, COIN_DBL_MAX};
    const double       obj[]   = {-5.0, -4.0};
    const double       rowlb[] = {-COIN_DBL_MAX, -COIN_DBL_MAX};
    const double       rowub[] = {24.0, 6.0};

    solver.loadProblem(ncol, nrow, start, index, value,
                       collb, colub, obj, rowlb, rowub);
    solver.setInteger(0);
    solver.setInteger(1);

    /* 先单独确认 LP 松弛确实是分数的 —— 否则这个测试验不到分支定界 */
    solver.initialSolve();
    {
        /* 读解之前必须确认求解成功：失败时 getColSolution() 返回的不是计算结果，
         * 后面「y 是否为 1.5」这条前提断言就会以误导性的方式失败 ——
         * 看起来像模型建错了，其实是求解器没跑成。 */
        if (!solver.isProvenOptimal()) {
            std::printf("FAIL LP 松弛未求到最优，无法验证分支定界前提\n");
            return 1;
        }
        const double *r = solver.getColSolution();
        if (std::fabs(r[1] - 1.5) > 1e-6) {
            std::printf("FAIL LP 松弛 y=%.9f，本应为分数 1.5"
                        "（前提不成立，测试验不到分支定界）\n", r[1]);
            return 1;
        }
    }

    CbcModel model(solver);
    model.setLogLevel(0);
    model.messageHandler()->setLogLevel(0);
    model.branchAndBound();

    if (!model.isProvenOptimal()) {
        std::printf("FAIL 未证明整数最优：本问题可行且有界\n");
        return 1;
    }

    /* ① 整数最优值 —— 必须是 -20，不能是松弛的 -21 */
    {
        const double z = model.getObjValue();
        if (std::fabs(z - (-20.0)) > 1e-6) {
            std::printf("FAIL 整数最优值 %.9f != -20"
                        "（若为 -21 说明分支定界没生效，返回的是 LP 松弛）\n", z);
            return 1;
        }
    }

    /* ② 最优解逐分量 —— 目标值对了解也可能不对 */
    {
        const double *x = model.bestSolution();
        if (x == NULL) {
            std::printf("FAIL bestSolution() 为空\n");
            return 1;
        }
        if (std::fabs(x[0] - 4.0) > 1e-6 || std::fabs(x[1] - 0.0) > 1e-6) {
            std::printf("FAIL 整数最优解 (%.9f,%.9f) != (4,0)\n", x[0], x[1]);
            return 1;
        }
        /* ③ 解必须真的是整数（验取整链路，不只是碰巧数值接近） */
        for (int j = 0; j < ncol; ++j) {
            if (std::fabs(x[j] - std::floor(x[j] + 0.5)) > 1e-6) {
                std::printf("FAIL 第 %d 个变量 %.9f 不是整数\n", j, x[j]);
                return 1;
            }
        }
        /* ④ 解必须可行 */
        if (6.0 * x[0] + 4.0 * x[1] > 24.0 + 1e-6 ||
            x[0] + 2.0 * x[1] > 6.0 + 1e-6) {
            std::printf("FAIL 最优解违反约束\n");
            return 1;
        }
    }

    std::printf("Cbc OK: 分支定界求得整数最优 -20 @ (4,0)，"
                "严格优于 LP 松弛 -21，共 4 组断言\n");
    return 0;
}
