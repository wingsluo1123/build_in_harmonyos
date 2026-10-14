// test_package 消费者驱动：C++/Tree 映射的正/反双向断言。
#include "schema.hxx"

#include <cmath>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>

static int checks = 0;
static int failed = 0;

#define CHECK(cond)                                                     \
  do {                                                                  \
    ++checks;                                                           \
    if (!(cond)) {                                                      \
      ++failed;                                                         \
      std::cerr << "FAIL line " << __LINE__ << ": " #cond << std::endl; \
    }                                                                   \
  } while (false)

int main(int argc, char* argv[])
{
  if (argc != 4)
  {
    std::cerr << "usage: tree-driver <valid.xml> <invalid.xml> <schema.xsd>" << std::endl;
    return 2;
  }

  try
  {
    std::unique_ptr< ::test::Catalog > c = ::test::catalog(argv[1]);

    CHECK(c.get() != 0);
    CHECK(c->version() == 2);

    const ::test::Catalog::book_sequence& books = c->book();
    CHECK(books.size() == 2);

    if (books.size() == 2)
    {
      const ::test::Book& b0 = books[0];
      CHECK(b0.id() == "b1");
      CHECK(b0.title() == "Compiler Design");
      CHECK(std::fabs(b0.price() - 42.50) < 1e-9);
      CHECK(b0.tag().present());
      if (b0.tag().present())
        CHECK(b0.tag().get() == ::test::Tag::tech);

      const ::test::Book& b1 = books[1];
      CHECK(b1.id() == "b2");
      CHECK(b1.title() == "Poems");
      CHECK(std::fabs(b1.price() - 9.99) < 1e-9);
      CHECK(!b1.tag().present());
    }

    // 序列化回写 → 再解析 → 结构等价（生成代码的自洽闭环）。
    // 必须用 namespace_infomap 注入 xsi:schemaLocation，否则回写文档在
    // 校验模式下找不到 grammar（与上游 built-in 用例同款写法）。
    ::xml_schema::namespace_infomap map;
    map["t"].name = "urn:test";
    map["t"].schema = argv[3];

    std::ostringstream os;
    ::test::catalog(os, *c, map);
    CHECK(!os.str().empty());

    std::istringstream is(os.str());
    std::unique_ptr< ::test::Catalog > c2 = ::test::catalog(is, argv[1]);
    CHECK(c2.get() != 0);
    if (c2.get() != 0)
    {
      CHECK(c2->version() == c->version());
      CHECK(c2->book().size() == c->book().size());
      if (c2->book().size() == 2)
        CHECK(c2->book()[0].title() == c->book()[0].title());
    }

    // 反向用例：违反 schema 的实例必须被拒绝
    bool rejected = false;
    try
    {
      ::test::catalog(argv[2]);
    }
    catch (const ::xml_schema::exception&)
    {
      rejected = true;
    }
    CHECK(rejected);
  }
  catch (const ::xml_schema::exception& e)
  {
    std::cerr << "unexpected xml_schema exception: " << e << std::endl;
    return 1;
  }
  catch (const std::exception& e)
  {
    std::cerr << "unexpected exception: " << e.what() << std::endl;
    return 1;
  }

  std::cout << "TREE_CHECKS=" << checks << " TREE_FAILED=" << failed
            << std::endl;
  return failed == 0 ? 0 : 1;
}
