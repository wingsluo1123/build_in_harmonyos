// opennurbs 消费侧端到端测试：以「库使用者」身份真实调用几何 API。
// 只使用长期稳定的公开 API（点/向量/曲线/区间/变换/包围盒），
// 避免依赖不确定存在或参数签名易变的高级接口。
#include "opennurbs.h"

#include <cmath>
#include <cstdio>

static int failures = 0;

static void check(bool ok, const char* what)
{
  if (!ok) {
    ++failures;
    std::printf("FAIL  %s\n", what);
  } else {
    std::printf("PASS  %s\n", what);
  }
}

int main()
{
  // ① 点 / 距离
  const ON_3dPoint p0(1.0, 2.0, 3.0);
  const ON_3dPoint p1(4.0, 6.0, 3.0);
  check(std::fabs(p0.DistanceTo(p1) - 5.0) < 1e-12, "ON_3dPoint::DistanceTo");

  // ② 向量运算
  const ON_3dVector v = p1 - p0;
  check(std::fabs(v.Length() - 5.0) < 1e-12, "ON_3dVector::Length");
  check(std::fabs(v * ON_3dVector(1.0, 0.0, 0.0) - 3.0) < 1e-12, "dot product");

  // ③ 曲线：合法性 / 定义域 / 求值（PointAt 是 ON_Curve 的稳定接口；
  //    Evaluate 需要 4 个参数（含 side 与容差），不作为基线校验面）
  ON_LineCurve line(p0, p1);
  check(line.IsValid(), "ON_LineCurve::IsValid");
  const ON_Interval domain = line.Domain();
  check(domain.IsIncreasing(), "curve domain increasing");
  const ON_3dPoint mid = line.PointAt(domain.Mid());
  check(mid.DistanceTo(ON_3dPoint(2.5, 4.0, 3.0)) < 1e-12, "curve midpoint value");

  // ④ 变换：平移作用于点（用上游推荐的工厂方法；Translation() 已标 deprecated）
  const ON_Xform move =
      ON_Xform::TranslationTransformation(ON_3dVector(1.0, 1.0, 1.0));
  const ON_3dPoint moved = move * p0;
  check(moved.DistanceTo(ON_3dPoint(2.0, 3.0, 4.0)) < 1e-12, "ON_Xform translation");

  // ⑤ 包围盒：几何容器
  ON_BoundingBox box;
  box.Set(p0, false);
  box.Set(p1, true);
  check(box.IsValid(), "ON_BoundingBox::IsValid");
  check(std::fabs(box.Diagonal().Length() - 5.0) < 1e-12, "bounding box diagonal");

  std::printf("\n%s (%d failure(s))\n", failures ? "FAILURES" : "OK", failures);
  return failures ? 1 : 0;
}
