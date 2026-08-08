/*
 * Consumer test for graphene 1.10.8.
 * Initializes a vec4 and an identity matrix, then checks values.
 */
#include <graphene.h>
#include <stdio.h>

int main(void)
{
    graphene_vec4_t vec;
    graphene_matrix_t m;
    float x, y, z, w;
    float scale;

    graphene_vec4_init(&vec, 1.0f, 2.0f, 3.0f, 4.0f);
    x = graphene_vec4_get_x(&vec);
    y = graphene_vec4_get_y(&vec);
    z = graphene_vec4_get_z(&vec);
    w = graphene_vec4_get_w(&vec);

    if (x != 1.0f || y != 2.0f || z != 3.0f || w != 4.0f) {
        fprintf(stderr, "graphene vec4 value mismatch: %f %f %f %f\n",
                x, y, z, w);
        return 1;
    }

    graphene_matrix_init_identity(&m);
    scale = graphene_matrix_get_value(&m, 0, 0);
    if (scale != 1.0f) {
        fprintf(stderr, "graphene matrix identity check failed: %f\n", scale);
        return 2;
    }

    printf("graphene consumer checks passed\n");
    return 0;
}
