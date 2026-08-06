/* Clp 1.17.10 真实功能断言。
 *
 * 不用 dlopen 探针：解析到符号 ≠ 解得对。这里真的解一个**线性规划**，
 * 再跟手算的最优解逐分量对账。
 *
 *   min  -x0 - 2*x1
 *   s.t.  x0 +   x1 <= 4
 *         x0 + 3*x1 <= 6
 *         x0, x1 >= 0
 *
 * 可行域顶点：(0,0)=0、(4,0)=-4、(3,1)=-5、(0,2)=-4
 * → 最优值 -5，取在 (3,1)（两条约束同时紧）。
 * 这个解是**唯一**的（目标向量不平行于任一约束），所以可以卡紧容差。
 *
 * ⚠️ 头名是 ClpSimplex.hpp，不是 clp.h：COIN-OR 全系把头装在 include/coin/ 下、
 *    按 .hpp 命名。生成器的默认测试桩猜 `clp.h` 会直接编不过（实撞）。
 */
#include "ClpSimplex.hpp"

#include <cmath>
#include <cstdio>

int main(void)
{
    ClpSimplex model;
    model.setLogLevel(0);   /* 别把单纯法迭代日志混进验收输出 */

    const int    ncol = 2, nrow = 2;
    /* 列主序（column-major）：每列在各行上的系数 */
    const CoinBigIndex start[]  = {0, 2, 4};
    const int          index[]  = {0, 1, 0, 1};
    const double       value[]  = {1.0, 1.0, 1.0, 3.0};
    const double       collb[]  = {0.0, 0.0};
    const double       colub[]  = {COIN_DBL_MAX, COIN_DBL_MAX};
    const double       obj[]    = {-1.0, -2.0};
    const double       rowlb[]  = {-COIN_DBL_MAX, -COIN_DBL_MAX};
    const double       rowub[]  = {4.0, 6.0};

    model.loadProblem(ncol, nrow, start, index, value,
                      collb, colub, obj, rowlb, rowub);

    if (model.numberColumns() != ncol || model.numberRows() != nrow) {
        std::printf("FAIL 模型规模 %dx%d != 2x2\n",
                    model.numberRows(), model.numberColumns());
        return 1;
    }

    model.primal();

    /* ① 必须求到最优（不是不可行、无界或迭代上限） */
    if (!model.isProvenOptimal()) {
        std::printf("FAIL 未求到最优：status=%d（本问题有界且可行）\n", model.status());
        return 1;
    }

    /* ② 最优目标值 */
    {
        const double z = model.objectiveValue();
        if (std::fabs(z - (-5.0)) > 1e-7) {
            std::printf("FAIL 最优值 %.12f != -5\n", z);
            return 1;
        }
    }

    /* ③ 最优解逐分量 —— 只对目标值不够：错的顶点也可能凑巧同值 */
    {
        const double *x = model.primalColumnSolution();
        if (std::fabs(x[0] - 3.0) > 1e-7 || std::fabs(x[1] - 1.0) > 1e-7) {
            std::printf("FAIL 最优解 (%.12f,%.12f) != (3,1)\n", x[0], x[1]);
            return 1;
        }
    }

    /* ④ 两条约束都应取到紧（等号）——验行活动量的计算 */
    {
        const double *row = model.primalRowSolution();
        if (std::fabs(row[0] - 4.0) > 1e-7 || std::fabs(row[1] - 6.0) > 1e-7) {
            std::printf("FAIL 行活动量 (%.12f,%.12f) != (4,6)\n", row[0], row[1]);
            return 1;
        }
    }

    /* ⑤ 对偶解：两约束都紧，对偶变量应满足
     *      y0 +   y1 = -1   (x0 的既约成本为 0)
     *      y0 + 3*y1 = -2   (x1 的既约成本为 0)
     *    解得 y = (-0.5, -0.5)。验对偶单纯法这条独立代码路径。 */
    {
        const double *y = model.dualRowSolution();
        if (std::fabs(y[0] - (-0.5)) > 1e-7 || std::fabs(y[1] - (-0.5)) > 1e-7) {
            std::printf("FAIL 对偶解 (%.12f,%.12f) != (-0.5,-0.5)\n", y[0], y[1]);
            return 1;
        }
    }

    std::printf("Clp OK: LP 最优值/最优解/行活动量/对偶解 共 5 组断言与手算吻合(<1e-7)\n");
    return 0;
}
