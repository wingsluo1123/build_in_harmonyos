// test_protobuf.cpp — protobuf 21.12 功能测试
// 测试覆盖：protoc 生成的代码编译、序列化/反序列化往返、repeated 字段、ByteSize
#include <iostream>
#include <string>
#include <cassert>
#include "person.pb.h"

int main() {
  // ── Test 1: 单消息序列化/反序列化往返 ──
  test::Person person;
  person.set_name("Alice");
  person.set_age(30);
  person.set_email("alice@example.com");
  person.set_active(true);
  person.add_tags("engineer");
  person.add_tags("admin");

  std::string data;
  bool ok = person.SerializeToString(&data);
  assert(ok && "SerializeToString failed");
  assert(!data.empty() && "Serialized data is empty");

  test::Person person2;
  ok = person2.ParseFromString(data);
  assert(ok && "ParseFromString failed");
  assert(person2.name() == "Alice" && "name mismatch");
  assert(person2.age() == 30 && "age mismatch");
  assert(person2.email() == "alice@example.com" && "email mismatch");
  assert(person2.active() == true && "active mismatch");
  assert(person2.tags_size() == 2 && "tags size mismatch");
  assert(person2.tags(0) == "engineer" && "tags[0] mismatch");
  assert(person2.tags(1) == "admin" && "tags[1] mismatch");

  // ── Test 2: AddressBook repeated 字段 ──
  test::AddressBook book;
  book.set_owner("manager");
  auto* p1 = book.add_people();
  p1->set_name("Bob");
  p1->set_age(25);
  auto* p2 = book.add_people();
  p2->set_name("Charlie");
  p2->set_age(35);
  p2->set_active(false);

  std::string book_data;
  book.SerializeToString(&book_data);
  assert(!book_data.empty() && "AddressBook serialization failed");

  test::AddressBook book2;
  ok = book2.ParseFromString(book_data);
  assert(ok && "AddressBook parse failed");
  assert(book2.owner() == "manager" && "owner mismatch");
  assert(book2.people_size() == 2 && "people size mismatch");
  assert(book2.people(0).name() == "Bob" && "people[0].name mismatch");
  assert(book2.people(0).age() == 25 && "people[0].age mismatch");
  assert(book2.people(1).name() == "Charlie" && "people[1].name mismatch");
  assert(book2.people(1).age() == 35 && "people[1].age mismatch");
  assert(book2.people(1).active() == false && "people[1].active mismatch");

  // ── Test 3: ByteSizeLong 一致性 ──
  size_t size1 = person.ByteSizeLong();
  size_t size2 = person2.ByteSizeLong();
  assert(size1 == size2 && "ByteSizeLong mismatch after round-trip");
  assert(size1 > 0 && "ByteSizeLong is zero");

  // ── Test 4: 默认值行为 (proto3 semantics) ──
  test::Person empty;
  assert(empty.name() == "" && "default name should be empty string");
  assert(empty.age() == 0 && "default age should be 0");
  assert(empty.active() == false && "default active should be false");
  assert(empty.tags_size() == 0 && "default tags should be empty");

  // ── Test 5: 清空字段 ──
  test::Person p;
  p.set_name("Test");
  p.clear_name();
  assert(p.name() == "" && "clear_name failed");

  std::cout << "All protobuf tests passed (5/5): "
            << "serialize/deserialize, repeated fields, byte size, "
            << "default values, field clear" << std::endl;
  return 0;
}
