/* Consumer-side end-to-end executor for the packaged par_shapes header.
 *
 * This file defines PAR_SHAPES_IMPLEMENTATION itself and only includes
 * "par_shapes.h" as installed by the package, so the executable cannot build
 * or pass when the package is missing or its header is stale (R34).
 *
 * Every case runs independently and reports TEST PASS / TEST FAIL on its own
 * line; the last line is a machine-readable summary and the process exit code
 * is non-zero when any case fails.
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#define PAR_SHAPES_IMPLEMENTATION
#include "par_shapes.h"

static int g_checks = 0;
static int g_check_failures = 0;
static int g_cases_run = 0;
static int g_cases_failed = 0;
static int g_case_failed = 0;

static void begin_case(const char *name)
{
    g_case_failed = 0;
    printf("== case: %s\n", name);
}

static void check(int ok, const char *what)
{
    g_checks++;
    if (!ok) {
        g_case_failed = 1;
        g_check_failures++;
        printf("  CHECK FAIL: %s\n", what);
    }
}

static void check_near(float got, float want, float tol, const char *what)
{
    g_checks++;
    if (!(fabsf(got - want) <= tol)) {
        g_case_failed = 1;
        g_check_failures++;
        printf("  CHECK FAIL: %s (got %g, want %g, tol %g)\n",
               what, (double) got, (double) want, (double) tol);
    }
}

static void end_case(const char *name)
{
    g_cases_run++;
    if (g_case_failed) {
        g_cases_failed++;
        printf("TEST FAIL: %s\n", name);
    } else {
        printf("TEST PASS: %s\n", name);
    }
    fflush(stdout);
}

static float vec_len3(const float *v)
{
    return sqrtf(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

static int finite3(const float *v)
{
    return isfinite(v[0]) && isfinite(v[1]) && isfinite(v[2]);
}

/* --- case 1: platonic solid topology and attribute layout ------------------ */
static void case_cube_topology(void)
{
    par_shapes_mesh *m = par_shapes_create_cube();
    check(m != NULL, "create_cube returns a mesh");
    if (m) {
        int in_unit = 1;
        check(m->points != NULL && m->triangles != NULL,
              "cube array storage is allocated");
        check(m->npoints == 8, "cube has 8 points");
        check(m->ntriangles == 12, "cube has 12 triangles");
        check(m->normals == NULL && m->tcoords == NULL,
              "cube carries no attribute arrays (documented)");
        for (int i = 0; i < m->npoints * 3; i++) {
            float c = m->points[i];
            if (fabsf(c) > 1e-6f && fabsf(c - 1.0f) > 1e-6f) {
                in_unit = 0;
            }
        }
        check(in_unit, "cube coordinates are all 0 or 1");
        par_shapes_free_mesh(m);
    }
}

/* --- case 2: subdivided sphere welding and unit normals -------------------- */
static void case_subdivided_sphere_normals(void)
{
    par_shapes_mesh *m = par_shapes_create_subdivided_sphere(2);
    check(m != NULL, "create_subdivided_sphere(2) returns a mesh");
    if (m) {
        int on_sphere = 1, unit_normals = 1;
        check(m->npoints > 0 && m->ntriangles > 0, "subdivided sphere is non-empty");
        check(m->normals != NULL, "subdivided sphere carries normals");
        check(m->tcoords == NULL, "subdivided sphere has no tcoords");
        for (int i = 0; i < m->npoints; i++) {
            if (fabsf(vec_len3(m->points + 3 * i) - 1.0f) > 1e-4f) {
                on_sphere = 0;
            }
        }
        check(on_sphere, "subdivided sphere points lie on the unit sphere");
        if (m->normals) {
            for (int i = 0; i < m->npoints; i++) {
                if (fabsf(vec_len3(m->normals + 3 * i) - 1.0f) > 1e-4f) {
                    unit_normals = 0;
                }
            }
        }
        check(unit_normals, "subdivided sphere normals are unit length");
        par_shapes_free_mesh(m);
    }
}

/* --- case 3: parametric cylinder counting and input guards ----------------- */
static void case_parametric_cylinder_counts(void)
{
    par_shapes_mesh *m = par_shapes_create_cylinder(5, 6);
    check(m != NULL, "create_cylinder(5, 6) returns a mesh");
    if (m) {
        check(m->npoints == 42, "cylinder(5, 6) has (5+1)*(6+1) = 42 points");
        check(m->ntriangles == 60, "cylinder(5, 6) has 2*5*6 = 60 triangles");
        check(m->normals != NULL && m->tcoords != NULL,
              "cylinder carries tcoords and welded normals");
        par_shapes_free_mesh(m);
    }
    check(par_shapes_create_cylinder(2, 6) == NULL, "cylinder rejects slices < 3");
    check(par_shapes_create_cylinder(5, 0) == NULL, "cylinder rejects stacks < 1");
}

/* --- case 4: parametric sphere counting after degenerate removal ----------- */
static void case_parametric_sphere_counts(void)
{
    par_shapes_mesh *m = par_shapes_create_parametric_sphere(12, 13);
    check(m != NULL, "create_parametric_sphere(12, 13) returns a mesh");
    if (m) {
        int unit_normals = 1;
        check(m->ntriangles == 288,
              "parametric_sphere(12, 13) has 12*2 + (13-2)*12*2 = 288 triangles");
        check(m->normals != NULL && m->tcoords != NULL,
              "parametric sphere carries tcoords and welded normals");
        if (m->normals) {
            for (int i = 0; i < m->npoints; i++) {
                if (fabsf(vec_len3(m->normals + 3 * i) - 1.0f) > 1e-3f) {
                    unit_normals = 0;
                }
            }
        }
        check(unit_normals, "parametric sphere normals are unit length");
        par_shapes_free_mesh(m);
    }
}

/* --- case 5: plane generation stays finite in the z = 0 plane -------------- */
static void case_plane_finite_normals(void)
{
    par_shapes_mesh *m = par_shapes_create_plane(5, 6);
    check(m != NULL, "create_plane(5, 6) returns a mesh");
    if (m) {
        int on_plane = 1, finite = 1;
        check(m->npoints == 42, "plane(5, 6) has (5+1)*(6+1) = 42 points");
        check(m->normals != NULL && m->tcoords != NULL,
              "plane carries tcoords and welded normals");
        for (int i = 0; i < m->npoints; i++) {
            if (fabsf(m->points[3 * i + 2]) > 1e-5f) {
                on_plane = 0;
            }
            if (!finite3(m->points + 3 * i)) {
                finite = 0;
            }
            if (m->normals && !finite3(m->normals + 3 * i)) {
                finite = 0;
            }
        }
        check(on_plane, "plane points lie on z = 0");
        check(finite, "plane points and normals are finite (no NaN)");
        par_shapes_free_mesh(m);
    }
}

/* --- case 6: merge concatenation, index offsets and attribute copy --------- */
static void case_merge_counts_and_offsets(void)
{
    par_shapes_mesh *a = par_shapes_create_klein_bottle(10, 20);
    par_shapes_mesh *b = par_shapes_create_plane(3, 3);
    check(a != NULL && b != NULL, "klein bottle and plane are both created");
    if (a && b) {
        int a_points = a->npoints, a_tris = a->ntriangles;
        int b_points = b->npoints, b_tris = b->ntriangles;
        PAR_SHAPES_T b_first_index = b->triangles[0];
        /* R1 检视整改：tcoords 属可选属性，读取前先判空（此前对称性不对称，
           b 侧缺守卫；空时退化为 0.0f 让校验点干净失败而非空指针崩溃）。 */
        float b_last_uv = b->tcoords ? b->tcoords[2 * b_points - 1] : 0.0f;

        check(a_points == 231, "klein_bottle(10, 20) has (10+1)*(20+1) = 231 points");
        check(a_tris == 400, "klein_bottle(10, 20) has 2*10*20 = 400 triangles");

        par_shapes_merge(a, b);

        check(a->npoints == a_points + b_points, "merge concatenates point counts");
        check(a->ntriangles == a_tris + b_tris, "merge concatenates triangle counts");
        check(a->triangles[3 * a_tris] == (PAR_SHAPES_T) (a_points + b_first_index),
              "merge offsets merged triangle indices by the old point count");
        /* R1 检视整改：原校验只比较末点 z 分量（平面网格上恒为 0.0f，自比无从
           检出错误分量拷贝）；改为末点三分量逐字节比对，索引以 a->npoints 为界，
           即使计数错误也不越界读。 */
        int last_point_copied = (a->npoints == a_points + b_points) &&
            memcmp(a->points + 3 * (a->npoints - 1),
                   b->points + 3 * (b_points - 1), 3 * sizeof(float)) == 0;
        check(last_point_copied, "merged point block copies src points verbatim");
        check(a->tcoords != NULL &&
              a->tcoords[2 * (a_points + b_points) - 1] == b_last_uv,
              "merged tcoords block copies src tcoords verbatim");
        par_shapes_free_mesh(a);
        par_shapes_free_mesh(b);
    } else {
        if (a) {
            par_shapes_free_mesh(a);
        }
        if (b) {
            par_shapes_free_mesh(b);
        }
    }
}

/* --- case 7: merge_and_free consumes the source mesh ----------------------- */
static void case_merge_and_free_ownership(void)
{
    par_shapes_mesh *a = par_shapes_create_cube();
    par_shapes_mesh *b = par_shapes_create_cube();
    check(a != NULL && b != NULL, "two cubes are created");
    if (a && b) {
        par_shapes_merge_and_free(a, b); /* consumes b */
        check(a->npoints == 16, "merge_and_free doubles the point count");
        check(a->ntriangles == 24, "merge_and_free doubles the triangle count");
        check(a->points != NULL && a->triangles != NULL, "surviving mesh stays valid");
        par_shapes_free_mesh(a);
    } else {
        if (a) {
            par_shapes_free_mesh(a);
        }
        if (b) {
            par_shapes_free_mesh(b);
        }
    }
}

/* --- case 8: clone reuses a target mesh when growing and shrinking --------- */
static void case_clone_reuse(void)
{
    par_shapes_mesh *src = par_shapes_create_subdivided_sphere(1);
    par_shapes_mesh *dst = par_shapes_create_cube();
    check(src != NULL && dst != NULL, "source sphere and target cube are created");
    if (src && dst) {
        par_shapes_mesh *r = par_shapes_clone(src, dst);
        int same_points = (r->npoints == src->npoints);
        int same_tris = (r->ntriangles == src->ntriangles);
        int same_pts_data = same_points &&
            memcmp(r->points, src->points, 3 * sizeof(float) * src->npoints) == 0;
        /* R1 检视整改：法线窗口比对补上与点位同为 same_points 短路——clone 未按
           源点数扩容时，r->normals 窗口会越过堆缓冲（ASAN abort 而非干净失败）。 */
        int same_nrm_data = same_points && (src->normals && r->normals) &&
            memcmp(r->normals, src->normals, 3 * sizeof(float) * src->npoints) == 0;
        check(same_points, "clone copies the point count into the target");
        check(same_tris, "clone copies the triangle count into the target");
        check(same_pts_data, "clone copies point data verbatim");
        check(same_nrm_data, "clone copies normal data verbatim");
        par_shapes_free_mesh(src);
        par_shapes_free_mesh(dst);
    } else {
        if (src) {
            par_shapes_free_mesh(src);
        }
        if (dst) {
            par_shapes_free_mesh(dst);
        }
    }
}

/* --- case 9: translation shifts the bounding box exactly ------------------- */
static void case_translate_aabb(void)
{
    par_shapes_mesh *m = par_shapes_create_cube();
    check(m != NULL, "cube is created");
    if (m) {
        float before[6], after[6];
        par_shapes_compute_aabb(m, before);
        par_shapes_translate(m, 2.5f, -1.0f, 0.5f);
        par_shapes_compute_aabb(m, after);
        check_near(before[0], 0.0f, 1e-6f, "cube min x before translate");
        check_near(before[3], 1.0f, 1e-6f, "cube max x before translate");
        check_near(after[0], 2.5f, 1e-6f, "min x is translated by +2.5");
        check_near(after[1], -1.0f, 1e-6f, "min y is translated by -1.0");
        check_near(after[2], 0.5f, 1e-6f, "min z is translated by +0.5");
        check_near(after[3], 3.5f, 1e-6f, "max x is translated by +2.5");
        check_near(after[4], 0.0f, 1e-6f, "max y is translated by -1.0");
        check_near(after[5], 1.5f, 1e-6f, "max z is translated by +0.5");
        par_shapes_free_mesh(m);
    }
}

/* --- case 10: non-uniform scale multiplies the bounding box componentwise -- */
static void case_scale_aabb(void)
{
    par_shapes_mesh *m = par_shapes_create_plane(3, 3);
    check(m != NULL, "plane is created");
    if (m) {
        float before[6], after[6];
        float fs[3] = {2.0f, 3.0f, 1.0f};
        int scaled = 1;
        par_shapes_compute_aabb(m, before);
        par_shapes_scale(m, fs[0], fs[1], fs[2]);
        par_shapes_compute_aabb(m, after);
        for (int i = 0; i < 6; i++) {
            float want = before[i] * fs[i % 3];
            if (fabsf(after[i] - want) > 1e-4f * (fabsf(want) + 1.0f)) {
                scaled = 0;
            }
        }
        check(scaled, "aabb scales componentwise with the given factors");
        check(after[3] - after[0] > 0.0f && after[4] - after[1] > 0.0f,
              "scaled aabb keeps positive x/y extents");
        par_shapes_free_mesh(m);
    }
}

/* --- case 11: a full 2*pi rotation returns to the original pose ------------ */
static void case_rotate_roundtrip(void)
{
    par_shapes_mesh *a = par_shapes_create_subdivided_sphere(2);
    par_shapes_mesh *b = par_shapes_create_subdivided_sphere(2);
    check(a != NULL && b != NULL, "two identical spheres are created");
    if (a && b) {
        const float zaxis[3] = {0.0f, 0.0f, 1.0f};
        int same = (a->npoints == b->npoints && a->ntriangles == b->ntriangles);
        par_shapes_rotate(a, 2.0f * (float) PAR_PI, zaxis);
        if (same) {
            for (int i = 0; i < a->npoints * 3; i++) {
                if (fabsf(a->points[i] - b->points[i]) > 1e-4f) {
                    same = 0;
                }
                if (a->normals && b->normals &&
                    fabsf(a->normals[i] - b->normals[i]) > 1e-4f) {
                    same = 0;
                }
            }
        }
        check(same, "rotating by 2*pi about z returns to the original pose");
        par_shapes_free_mesh(a);
        par_shapes_free_mesh(b);
    } else {
        if (a) {
            par_shapes_free_mesh(a);
        }
        if (b) {
            par_shapes_free_mesh(b);
        }
    }
}

/* --- helper: scan an OBJ file produced by par_shapes_export ---------------- */
static int obj_scan(const char *path, int *n_v, int *n_vn, int *n_vt, int *n_f,
                    int *double_slash)
{
    char line[512];
    FILE *f = fopen(path, "r");
    if (!f) {
        return 0;
    }
    *n_v = 0;
    *n_vn = 0;
    *n_vt = 0;
    *n_f = 0;
    *double_slash = 0;
    while (fgets(line, sizeof(line), f)) {
        if (strncmp(line, "v ", 2) == 0) {
            (*n_v)++;
        } else if (strncmp(line, "vn ", 3) == 0) {
            (*n_vn)++;
        } else if (strncmp(line, "vt ", 3) == 0) {
            (*n_vt)++;
        } else if (strncmp(line, "f ", 2) == 0) {
            (*n_f)++;
            if (!*double_slash && strstr(line, "//") != NULL) {
                *double_slash = 1;
            }
        }
    }
    fclose(f);
    return 1;
}

/* --- case 12: asset-pipeline end-to-end (transform -> export -> re-read) --- */
static void case_e2e_pipeline(void)
{
    par_shapes_mesh *m = par_shapes_create_subdivided_sphere(2);
    check(m != NULL, "subdivided sphere is created");
    if (m) {
        const float zaxis[3] = {0.0f, 0.0f, 1.0f};
        int n_v = 0, n_vn = 0, n_vt = 0, n_f = 0, double_slash = 0;
        float aabb[6];
        int opened;

        par_shapes_scale(m, 2.0f, 2.0f, 2.0f);
        par_shapes_rotate(m, (float) PAR_PI / 3.0f, zaxis);
        par_shapes_translate(m, 0.5f, -1.0f, 0.25f);
        par_shapes_compute_aabb(m, aabb);
        check((aabb[3] - aabb[0]) <= 4.01f && (aabb[4] - aabb[1]) <= 4.01f &&
              (aabb[5] - aabb[2]) <= 4.01f,
              "scaled/rotated/translated sphere keeps its 4-unit diameter bound");

        par_shapes_export(m, "consumer_par_shapes_e2e.obj");
        opened = obj_scan("consumer_par_shapes_e2e.obj",
                          &n_v, &n_vn, &n_vt, &n_f, &double_slash);
        check(opened, "exported OBJ file can be reopened");
        if (opened) {
            check(n_v == m->npoints, "OBJ v-line count matches the mesh point count");
            check(n_vn == m->npoints, "OBJ vn-line count matches the point count");
            check(n_vt == 0, "normals-only mesh writes no vt lines");
            check(n_f == m->ntriangles, "OBJ f-line count matches the triangle count");
            check(double_slash, "normals-only faces use the v//vn form");
        }
        par_shapes_free_mesh(m);
    }
}

int main(void)
{
    static const struct {
        const char *name;
        void (*fn)(void);
    } cases[] = {
        {"cube_topology", case_cube_topology},
        {"subdivided_sphere_normals", case_subdivided_sphere_normals},
        {"parametric_cylinder_counts", case_parametric_cylinder_counts},
        {"parametric_sphere_counts", case_parametric_sphere_counts},
        {"plane_finite_normals", case_plane_finite_normals},
        {"merge_counts_and_offsets", case_merge_counts_and_offsets},
        {"merge_and_free_ownership", case_merge_and_free_ownership},
        {"clone_reuse", case_clone_reuse},
        {"translate_aabb", case_translate_aabb},
        {"scale_aabb", case_scale_aabb},
        {"rotate_roundtrip", case_rotate_roundtrip},
        {"e2e_pipeline", case_e2e_pipeline},
    };
    int n = (int) (sizeof(cases) / sizeof(cases[0]));

    printf("par_shapes consumer E2E executor (%d cases)\n", n);
    for (int i = 0; i < n; i++) {
        begin_case(cases[i].name);
        cases[i].fn();
        end_case(cases[i].name);
    }
    printf("checks executed: %d, check failures: %d\n", g_checks, g_check_failures);
    printf("TEST SUMMARY: %d passed, %d failed\n",
           g_cases_run - g_cases_failed, g_cases_failed);
    return g_cases_failed ? 1 : 0;
}
