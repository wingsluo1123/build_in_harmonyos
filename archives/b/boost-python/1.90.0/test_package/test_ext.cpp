// test_package 消费者测试：真实 Boost.Python 扩展模块
#include <boost/python.hpp>

int add(int a, int b) { return a + b; }
std::string greet() { return "hello-from-boost-python"; }

BOOST_PYTHON_MODULE(test_ext) {
  using namespace boost::python;
  def("add", &add, "add two integers");
  def("greet", &greet, "return a greeting");
}
