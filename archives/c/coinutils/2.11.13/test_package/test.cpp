#include <cstdio>
#include <cstdlib>

#include "CoinPackedVector.hpp"
#include "CoinError.hpp"

int main(void) {
    try {
        CoinPackedVector vec;
        vec.insert(0, 1.0);
        vec.insert(1, 2.0);
        vec.insert(2, 3.0);

        if (vec.getNumElements() != 3) {
            printf("FAIL: expected 3 elements, got %d\n", vec.getNumElements());
            return 1;
        }

        double sum = 0.0;
        const double *elems = vec.getElements();
        for (int i = 0; i < vec.getNumElements(); i++) {
            sum += elems[i];
        }

        if (sum != 6.0) {
            printf("FAIL: expected sum 6.0, got %f\n", sum);
            return 1;
        }

        printf("coinutils test OK: CoinPackedVector with %d elements, sum=%f\n",
               vec.getNumElements(), sum);
        return 0;
    } catch (CoinError &e) {
        printf("FAIL: CoinError: %s\n", e.message().c_str());
        return 1;
    }
}
