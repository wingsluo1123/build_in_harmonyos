#include <proj.h>

#include <cmath>

int main() {
    PJ_CONTEXT *context = proj_context_create();
    if (context == nullptr) {
        return 1;
    }

    PJ *transform = proj_create_crs_to_crs(
        context, "EPSG:4326", "EPSG:3857", nullptr);
    if (transform == nullptr) {
        proj_context_destroy(context);
        return 2;
    }

    const PJ_COORD input = proj_coord(0.0, 0.0, 0.0, 0.0);
    const PJ_COORD output = proj_trans(transform, PJ_FWD, input);
    const bool valid = std::isfinite(output.xy.x) && std::isfinite(output.xy.y);
    const bool at_origin = std::fabs(output.xy.x) < 1e-9 &&
                           std::fabs(output.xy.y) < 1e-9;

    proj_destroy(transform);
    proj_context_destroy(context);
    return valid && at_origin ? 0 : 3;
}
