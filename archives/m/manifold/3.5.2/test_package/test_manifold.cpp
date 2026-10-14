// test_manifold.cpp — manifold 3.5.2 test_package consumer test.
// 真实 API 消费: Manifold 核心布尔、CrossSection (clipper2 后端)、
// manifoldc C 绑定、属性计算。断言值取自上游测试语义 (Cube/Extrude 等)。
#include <cmath>
#include <cstdio>
#include <cstdlib>

#include "manifold/manifold.h"
#include "manifold/cross_section.h"
#include "manifold/version.h"

#ifdef MANIFOLD_TEST_CBIND
#include "manifold/manifoldc.h"
#endif

using namespace manifold;

static int failures = 0;

#define CHECK(cond, msg)                                            \
  do {                                                              \
    if (cond) {                                                     \
      printf("PASS: %s\n", msg);                                    \
    } else {                                                        \
      printf("FAIL: %s\n", msg);                                    \
      failures++;                                                   \
    }                                                               \
  } while (0)

#define CHECK_NEAR(val, expect, tol, msg)                           \
  do {                                                              \
    double _v = (val);                                              \
    if (std::abs(_v - (expect)) < (tol)) {                          \
      printf("PASS: %s\n", msg);                                    \
    } else {                                                        \
      printf("FAIL: %s (got %.9f, expect %.9f)\n", msg, _v,         \
             static_cast<double>(expect));                          \
      failures++;                                                   \
    }                                                               \
  } while (0)

int main() {
  // --- 1. 构造 + 体积/表面积 (单位立方体) ---
  Manifold cube = Manifold::Cube(vec3(1.0), true);
  CHECK(std::abs(cube.Volume() - 1.0) < 1e-9, "cube volume == 1");
  CHECK(std::abs(cube.SurfaceArea() - 6.0) < 1e-9, "cube surface area == 6");
  CHECK(cube.NumVert() == 8, "cube NumVert == 8");

  // --- 2. 布尔运算: 两个重叠立方体 (语义 = 上游 DeterminismSimple* 用例) ---
  Manifold a = Manifold::Cube(vec3(1.0), true);
  Manifold b = Manifold::Cube(vec3(1.0), true).Translate(vec3(0.5, 0, 0));
  Manifold add = a + b;
  CHECK_NEAR(add.Volume(), 1.5, 1e-6, "boolean add volume == 1.5");
  Manifold sub = a - b;
  CHECK_NEAR(sub.Volume(), 0.5, 1e-6, "boolean subtract volume == 0.5");
  Manifold inter = a ^ b;
  CHECK_NEAR(inter.Volume(), 0.5, 1e-6, "boolean intersect volume == 0.5");
  CHECK(inter.Genus() == 0, "intersect genus == 0");

  // --- 3. 变换 ---
  Manifold scaled = a.Scale(vec3(2.0, 3.0, 4.0));
  CHECK(std::abs(scaled.Volume() - 24.0) < 1e-6, "scale volume == 24");
  Manifold moved = a.Translate(vec3(5.0));
  CHECK(std::abs(moved.Volume() - 1.0) < 1e-9, "translate keeps volume");

  // --- 4. CrossSection (2D, clipper2 后端) + Extrude ---
  // 语义来自上游 cross_section_test.cpp 的 Square 用例
  auto a3 = Manifold::Cube({5, 5, 5});
  auto b3 = Manifold::Extrude(CrossSection::Square({5, 5}).ToPolygons(), 5);
  CHECK(std::abs((a3 - b3).Volume()) < 1e-5, "Extrude(Square) == Cube");
  CrossSection sq = CrossSection::Square(vec2(1.0));
  CHECK(std::abs(sq.Area() - 1.0) < 1e-9, "cross section square area == 1");
  CrossSection sq2 = CrossSection::Square(vec2(1.0)).Translate(vec2(0.5));
  CrossSection sqUnion = sq + sq2;
  // Square(size) 以 size 为边长: 两个边长 1 的方块错开 0.5 →
  // 并集 1.75, 交集 0.25 (与 clipper2 精确多边形算术一致)
  CHECK_NEAR(sqUnion.Area(), 1.75, 1e-9, "cross section union area == 1.75");
  CrossSection sqInter = sq ^ sq2;
  CHECK_NEAR(sqInter.Area(), 0.25, 1e-9, "cross section intersect area == 0.25");

  // --- 5. 球体 + 网格导出 + 简化 ---
  Manifold sphere = Manifold::Sphere(1.0, 32);
  // 32 段内接多面体体积略小于解析球: 4.0952 (上游同参数数值)
  CHECK_NEAR(sphere.Volume(), 4.095220101, 1e-4, "sphere volume == 4.0952");
  MeshGL meshGL = sphere.GetMeshGL();
  CHECK(meshGL.NumVert() > 0 && meshGL.NumTri() > 0, "GetMeshGL non-empty");

  Manifold simplified = sphere.Simplify(0.1);
  CHECK(simplified.NumTri() < sphere.NumTri(), "Simplify reduces triangles");

  // --- 6. manifoldc (C 绑定) ---
#ifdef MANIFOLD_TEST_CBIND
  // C API 契约 (上游 manifoldc_test.cpp 同款): 调用方以 malloc 提供
  // manifold_manifold_size() 字节的内存, placement-new 风格构造, 返回同指针。
  void* c1_mem = malloc(manifold_manifold_size());
  void* c2_mem = malloc(manifold_manifold_size());
  void* c2t_mem = malloc(manifold_manifold_size());
  void* cr_mem = malloc(manifold_manifold_size());
  ManifoldManifold* c1 = manifold_cube(c1_mem, 1.0, 1.0, 1.0, 0);
  double vol = manifold_volume(c1);
  CHECK(std::abs(vol - 1.0) < 1e-9, "cbind manifold_cube volume == 1");
  ManifoldManifold* c2 = manifold_cube(c2_mem, 1.0, 1.0, 1.0, 0);
  // manifold_translate 为值语义 (结果写入新 buffer, 原对象不动), 不可 in-place
  ManifoldManifold* c2t = manifold_translate(c2t_mem, c2, 0.5, 0.0, 0.0);
  // 语义与上方 C++ 段一致: 错开 0.5 的两个单位立方体 → 并集体积 1.5
  ManifoldManifold* cr = manifold_boolean(cr_mem, c1, c2t, MANIFOLD_ADD);
  double vol2 = manifold_volume(cr);
  CHECK(std::abs(vol2 - 1.5) < 1e-6, "cbind boolean add volume == 1.5");
  CHECK(manifold_genus(cr) == 0, "cbind genus == 0");
  manifold_destruct_manifold(c1);
  manifold_destruct_manifold(c2);
  manifold_destruct_manifold(c2t);
  manifold_destruct_manifold(cr);
#endif

  // --- 7. 版本宏 (来自打包的 version.h) ---
  printf("manifold version: %d.%d.%d\n", MANIFOLD_VERSION_MAJOR,
         MANIFOLD_VERSION_MINOR, MANIFOLD_VERSION_PATCH);
  CHECK(MANIFOLD_VERSION_MAJOR == 3 && MANIFOLD_VERSION_MINOR == 5 &&
        MANIFOLD_VERSION_PATCH == 2, "version macros == 3.5.2");

  if (failures > 0) {
    printf("%d FAILURES\n", failures);
    return 1;
  }
  printf("ALL TESTS PASSED\n");
  return 0;
}
