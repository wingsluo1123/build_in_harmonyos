// Consumer test for mrgingham 1.26 — exercises the public C++ API.
//
// mrgingham::find_grid_from_points() takes integer point coordinates scaled by
// FIND_GRID_SCALE (1000; see the library's mrgingham-internal.h — its Voronoi
// core is integer-only) and returns the ordered lattice it detected.  We feed
// it a synthetic gridn x gridn lattice and verify that the returned grid is a
// correct permutation of the input points.

#include <mrgingham/mrgingham.hh>

#include <cmath>
#include <cstdio>
#include <vector>

static const int FIND_GRID_SCALE = 1000;

int main()
{
    const int gridn = 4;
    const int step  = 1000;   // 1.0 in mrgingham's scaled units

    std::vector<mrgingham::PointInt> points;
    for(int iy = 0; iy < gridn; iy++)
        for(int ix = 0; ix < gridn; ix++)
            // A small deterministic jitter avoids the Voronoi degeneracies of a
            // perfectly regular lattice (4 cells meeting at every vertex).
            points.push_back(mrgingham::PointInt(ix*step + (iy % 2) * 7,
                                                 iy*step + (ix % 2) * 11));

    std::vector<mrgingham::PointDouble> points_out;
    const bool ok = mrgingham::find_grid_from_points(points_out, points, gridn, false);

    if(!ok)
    {
        fprintf(stderr, "FAIL: find_grid_from_points() returned false\n");
        return 1;
    }
    if((int)points_out.size() != gridn*gridn)
    {
        fprintf(stderr, "FAIL: expected %d points, got %d\n",
                gridn*gridn, (int)points_out.size());
        return 1;
    }

    // Every returned point must coincide (within tolerance) with a distinct
    // input point — i.e. the grid is a permutation of the detections.
    std::vector<bool> used(points.size(), false);
    for(size_t i = 0; i < points_out.size(); i++)
    {
        const double x = points_out[i].x * FIND_GRID_SCALE;
        const double y = points_out[i].y * FIND_GRID_SCALE;

        size_t best  = points.size();
        double bestd = 1e30;
        for(size_t j = 0; j < points.size(); j++)
        {
            const double dx = x - points[j].x;
            const double dy = y - points[j].y;
            const double d  = dx*dx + dy*dy;
            if(d < bestd) { bestd = d; best = j; }
        }
        if(best == points.size() || std::sqrt(bestd) > 50.0)
        {
            fprintf(stderr,
                    "FAIL: returned point %zu (%.1f,%.1f) matches no input point\n",
                    i, x, y);
            return 1;
        }
        if(used[best])
        {
            fprintf(stderr, "FAIL: input point %zu matched twice\n", best);
            return 1;
        }
        used[best] = true;
    }

    printf("PASS: find_grid_from_points() recovered a %dx%d lattice (%d points)\n",
           gridn, gridn, (int)points_out.size());
    return 0;
}
