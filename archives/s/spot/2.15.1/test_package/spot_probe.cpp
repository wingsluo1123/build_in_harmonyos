// Consumer probe for spot/2.15.1 — 6 named cases over the public C++ API.
// Prints one "TEST <name>: PASS/FAIL" line per case, a final
// "TEST SUMMARY: n/m passed" line, and exits(1) if any case failed.
#include <cctype>
#include <iostream>
#include <sstream>
#include <string>

#include <spot/misc/version.hh>
#include <spot/tl/parse.hh>
#include <spot/tl/formula.hh>
#include <spot/twa/twagraph.hh>
#include <spot/twaalgos/translate.hh>
#include <spot/twaalgos/contains.hh>
#include <spot/twaalgos/hoa.hh>

static int total = 0;
static int failures = 0;

static void
check(const char* name, bool ok)
{
  ++total;
  if (!ok)
    ++failures;
  std::cout << "TEST " << name << ": " << (ok ? "PASS" : "FAIL") << '\n';
}

static spot::parsed_formula
parse(const char* s)
{
  return spot::parse_infix_psl(s);
}

int
main()
{
  // 1. Library version string.
  check("version_string", std::string(spot::version()) == "2.15.1");

  // 2. Parse + print round trip of a temporal formula.
  spot::parsed_formula pf = parse("a U b");
  bool parse_ok = pf.errors.empty() && pf.f != nullptr;
  std::ostringstream printed;
  if (parse_ok)
    printed << pf.f;
  check("parse_print_roundtrip", parse_ok && printed.str() == "a U b");

  // 3. Translation to a TGBA.
  spot::translator trans;
  spot::parsed_formula gf = parse("G F a");
  spot::twa_graph_ptr aut;
  if (gf.f != nullptr)
    aut = trans.run(gf.f);
  check("translate_gf_a",
        aut != nullptr && aut->num_states() >= 1 && aut->num_edges() >= 1);

  // 4. HOA serialization contains an acceptance condition.
  bool hoa_ok = false;
  if (aut != nullptr)
    {
      std::ostringstream hoa;
      spot::print_hoa(hoa, aut);
      std::string lower = hoa.str();
      for (char& c : lower)
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
      hoa_ok = lower.find("acceptance:") != std::string::npos;
    }
  check("hoa_serialization", hoa_ok);

  // 5. Positive language equivalence: a U b == b | (a & X(a U b)).
  spot::parsed_formula p1 = parse("a U b");
  spot::parsed_formula p2 = parse("b | (a & X(a U b))");
  bool eq_pos = p1.f != nullptr && p2.f != nullptr
    && spot::are_equivalent(p1.f, p2.f);
  check("equivalence_positive", eq_pos);

  // 6. Negative language equivalence: a != b.
  spot::parsed_formula p3 = parse("a");
  spot::parsed_formula p4 = parse("b");
  bool eq_neg = p3.f != nullptr && p4.f != nullptr
    && !spot::are_equivalent(p3.f, p4.f);
  check("equivalence_negative", eq_neg);

  std::cout << "TEST SUMMARY: " << (total - failures) << "/" << total
            << " passed" << std::endl;
  return failures == 0 ? 0 : 1;
}
