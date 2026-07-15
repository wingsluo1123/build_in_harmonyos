#include <CLI/CLI.hpp>
#include <string>
#include <iostream>

int main(int argc, char** argv) {
    CLI::App app{"CLI11 Test - OpenHarmony"};

    std::string name;
    app.add_option("--name", name, "Name to parse");

    try {
        app.parse(argc, argv);
    } catch (const CLI::ParseError& e) {
        return e.get_exit_code();
    }

    if (name == "OpenHarmony") {
        std::cout << "PASS: name parsed correctly" << std::endl;
        return 0;
    }
    std::cerr << "FAIL: expected 'OpenHarmony', got '" << name << "'" << std::endl;
    return 1;
}
