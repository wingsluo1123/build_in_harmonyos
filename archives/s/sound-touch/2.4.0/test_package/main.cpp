#include <iostream>
#include <soundtouch/SoundTouch.h>

int main() {
    soundtouch::SoundTouch st;
    st.setSampleRate(44100);
    st.setTempoChange(50.0f);
    std::cout << "SoundTouch version: " << st.getVersionString() << std::endl;
    return 0;
}
