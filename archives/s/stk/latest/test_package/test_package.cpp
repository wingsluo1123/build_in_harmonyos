#include <iostream>
#include "Stk.h"

int main(void) {
    stk::Stk::setSampleRate(44100.0);
    std::cout << "STK sample rate: " << stk::Stk::sampleRate() << std::endl;
    std::cout << "stk test OK" << std::endl;
    return 0;
}