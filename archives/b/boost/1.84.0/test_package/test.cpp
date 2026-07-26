#include <boost/date_time/posix_time/posix_time.hpp>
#include <boost/program_options.hpp>

#include <iostream>

int main() {
    namespace po = boost::program_options;
    po::options_description options("options");
    options.add_options()("count", po::value<int>()->default_value(7));
    char arg0[] = "boost_components_test";
    char arg1[] = "--count=7";
    char *argv[] = {arg0, arg1};
    po::variables_map values;
    po::store(po::parse_command_line(2, argv, options), values);
    po::notify(values);
    if (values["count"].as<int>() != 7) {
        std::cerr << "program_options failed\n";
        return 1;
    }
    const auto time = boost::posix_time::time_from_string("2024-01-02 03:04:05");
    if (boost::posix_time::to_iso_extended_string(time) != "2024-01-02T03:04:05") {
        std::cerr << "date_time failed\n";
        return 1;
    }
    std::cout << "Boost program_options + date_time: PASS\n";
    return 0;
}
