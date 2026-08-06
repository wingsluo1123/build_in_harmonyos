/* Cgl 0.60.9 真实功能断言。
 *
 * Cgl 是**割平面生成器**，它的职责不是"解出答案"，而是产出能把当前分数解
 * 切掉的有效不等式。所以断言要落在这件事本身上：
 *   ① LP 松弛的最优解确实是分数的（否则割平面无从谈起，测试就没验到东西）
 *   ② Gomory 割真的生成出来了
 *   ③ 生成的割**确实被当前分数解违反** —— 即它真的切掉了那个点
 *
 * ③ 是关键：只断言"生成了 N 条割"很弱，一条恒成立的废割也算生成。
 *
 *   max 5x + 4y   （内部按 min -5x -4y）
 *   s.t. 6x + 4y <= 24
 *         x + 2y <=  6
 *        x, y >= 0 且为整数
 *
 * LP 松弛最优：(3, 1.5)，目标 21 —— y 分数，正是割平面要处理的形态。
 */
#include "CglGomory.hpp"
#include "OsiClpSolverInterface.hpp"
#include "OsiCuts.hpp"

#include <cmath>
#include <cstdio>

int main(void)
{
    OsiClpSolverInterface si;
    si.messageHandler()->setLogLevel(0);

    const int    ncol = 2, nrow = 2;
    const CoinBigIndex start[] = {0, 2, 4};
    const int          index[] = {0, 1, 0, 1};
    const double       value[] = {6.0, 1.0, 4.0, 2.0};
    const double       collb[] = {0.0, 0.0};
    const double       colub[] = {COIN_DBL_MAX, COIN_DBL_MAX};
    const double       obj[]   = {-5.0, -4.0};
    const double       rowlb[] = {-COIN_DBL_MAX, -COIN_DBL_MAX};
    const double       rowub[] = {24.0, 6.0};

    si.loadProblem(ncol, nrow, start, index, value,
                   collb, colub, obj, rowlb, rowub);
    si.setInteger(0);
    si.setInteger(1);

    si.initialSolve();
    if (!si.isProvenOptimal()) {
        std::printf("FAIL LP 松弛未求到最优\n");
        return 1;
    }

    /* ① 松弛解必须是 (3, 1.5)：确认这确实是个「有分数、值得割」的局面 */
    {
        const double *x = si.getColSolution();
        if (std::fabs(x[0] - 3.0) > 1e-6 || std::fabs(x[1] - 1.5) > 1e-6) {
            std::printf("FAIL LP 松弛解 (%.9f,%.9f) != (3,1.5)\n", x[0], x[1]);
            return 1;
        }
        if (std::fabs(si.getObjValue() - (-21.0)) > 1e-6) {
            std::printf("FAIL LP 松弛目标 %.9f != -21\n", si.getObjValue());
            return 1;
        }
    }

    /* ② 生成 Gomory 割 */
    OsiCuts cuts;
    {
        CglGomory gomory;
        gomory.setLimit(10);
        gomory.generateCuts(si, cuts);
        if (cuts.sizeRowCuts() <= 0) {
            std::printf("FAIL 未生成任何行割（分数解 y=1.5 处 Gomory 应能出割）\n");
            return 1;
        }
    }

    /* ③ 至少一条割真的切掉当前分数解 —— 光"有割"不算数 */
    {
        const double *x = si.getColSolution();
        int cutting = 0;
        for (int i = 0; i < cuts.sizeRowCuts(); ++i) {
            if (cuts.rowCut(i).violated(x) > 1e-7) {
                ++cutting;
            }
        }
        if (cutting == 0) {
            std::printf("FAIL 生成了 %d 条割，但没有一条被当前分数解违反"
                        "（等于没切到东西）\n", cuts.sizeRowCuts());
            return 1;
        }
        std::printf("Cgl OK: LP 松弛 (3,1.5)/-21 吻合，Gomory 出 %d 条割、"
                    "其中 %d 条切掉了该分数解\n", cuts.sizeRowCuts(), cutting);
    }

    return 0;
}
