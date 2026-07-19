#include <iostream>
#include "Stk.h"

int main(void) {
    stk::Stk::setSampleRate(44100.0);
    const double sample_rate = stk::Stk::sampleRate();
    if (sample_rate != 44100.0) {
        std::cerr << "Unexpected STK sample rate: " << sample_rate << std::endl;
        return 1;
    }
    std::cout << "STK sample rate: " << sample_rate << std::endl;
    std::cout << "stk test OK" << std::endl;
    return 0;
}
