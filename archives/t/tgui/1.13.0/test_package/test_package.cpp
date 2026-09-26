#include <TGUI/TGUI.hpp>
#include <iostream>

int main() {
    // Test basic TGUI functionality without requiring display device
    
    // 1. Test String class
    tgui::String str("Hello TGUI");
    if (str.empty()) {
        std::cerr << "FAIL: String should not be empty\n";
        return 1;
    }
    
    // 2. Test Layout
    tgui::Layout layout("100");
    if (layout.getValue() != 100.0f) {
        std::cerr << "FAIL: Layout value mismatch\n";
        return 1;
    }
    
    // 3. Test Color
    tgui::Color color(255, 128, 64);
    if (color.getRed() != 255 || color.getGreen() != 128 || color.getBlue() != 64) {
        std::cerr << "FAIL: Color values mismatch\n";
        return 1;
    }
    
    std::cout << "TGUI test_package: All basic API tests passed\n";
    return 0;
}
