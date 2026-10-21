// Consumer test for durak 2.1.1 (conan test_package L1 test).
// Uses ONLY the installed public headers (<durak/game.hxx> etc.) and the
// public API (Game, Card, GameOption, playerStartsAttack, playerDefends,
// getTable, countOfNotBeatenCardsOnTable, operator<<).
// Plays a deterministic round and verifies observable results.

#include <durak/game.hxx>
#include <durak/card.hxx>
#include <durak/print.hxx>

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

int
main ()
{
  using namespace durak;

  // Fixed hands via the public GameOption.cardsInHands API (deterministic,
  // independent of deck shuffle). p1 attacks with 4C; p2's first card 7C
  // beats it (same symbol clubs, higher value; beats() ignores trump for
  // same-symbol comparison).
  auto option = GameOption{};
  option.cardsInHands = std::vector<std::vector<Card>>{
    { { 4, Type::clubs }, { 8, Type::hearts }, { 3, Type::clubs }, { 9, Type::diamonds }, { 2, Type::spades }, { 6, Type::hearts } },
    { { 7, Type::clubs }, { 5, Type::diamonds }, { 8, Type::spades }, { 3, Type::hearts }, { 9, Type::spades }, { 2, Type::diamonds } }
  };

  Game game{ { "consumer1", "consumer2" }, option };

  // 1) Observable: each player is dealt exactly the 6 cards handed in.
  auto const &players = game.getPlayers ();
  if (players.size () != 2)
    {
      std::cerr << "FAIL: expected 2 players, got " << players.size () << std::endl;
      return 1;
    }
  for (auto const &player : players)
    {
      if (player.getCards ().size () != 6)
        {
          std::cerr << "FAIL: expected 6 cards per player, got " << player.getCards ().size () << std::endl;
          return 1;
        }
    }
  std::cout << "dealt 6 cards to each of " << players.size () << " players" << std::endl;

  // 2) Observable: print.hxx operator<< output format for a Card.
  std::ostringstream oss;
  oss << Card{ 6, Type::hearts };
  std::string printed = oss.str ();
  std::cout << "card print: " << printed << std::endl;
  if (printed.find ("Card: {6 , hearts}") == std::string::npos)
    {
      std::cerr << "FAIL: unexpected card print output: " << printed << std::endl;
      return 1;
    }

  // 3) Observable: attacking player starts an attack with his first card (4C).
  auto const &attacker = players.at (0);
  if (not game.playerStartsAttack (std::vector<Card>{ attacker.getCards ().front () }))
    {
      std::cerr << "FAIL: playerStartsAttack returned false for a card in hand" << std::endl;
      return 1;
    }
  std::cout << "attack started, table has " << game.getTable ().size () << " card(s)" << std::endl;
  if (game.getTable ().size () != 1)
    {
      std::cerr << "FAIL: expected 1 card on table after attack, got " << game.getTable ().size () << std::endl;
      return 1;
    }

  // 4) Observable: countOfNotBeatenCardsOnTable after the attack.
  if (game.countOfNotBeatenCardsOnTable () != 1)
    {
      std::cerr << "FAIL: expected 1 not-beaten card on table" << std::endl;
      return 1;
    }

  // 5) Observable: defending player beats the attack: 7C covers 4C (same symbol
  //    clubs, higher value, clubs is the trump suit).
  auto const &defender = players.at (1);
  Card const &cardToBeat = game.getTable ().front ().first;
  bool defended = game.playerDefends (cardToBeat, defender.getCards ().front ());
  std::cout << "defend attempt result: " << (defended ? "success" : "failed") << std::endl;
  if (not defended)
    {
      std::cerr << "FAIL: expected 7C to cover 4C (same symbol, higher value)" << std::endl;
      return 1;
    }
  if (game.countOfNotBeatenCardsOnTable () != 0)
    {
      std::cerr << "FAIL: expected 0 not-beaten cards after successful defend" << std::endl;
      return 1;
    }

  // 6) Observable: round is set and game state is queryable.
  std::cout << "round = " << game.getRound () << std::endl;
  if (game.getRound () < 1)
    {
      std::cerr << "FAIL: round should be >= 1" << std::endl;
      return 1;
    }

  std::cout << "CONSUMER TEST PASSED: durak public API usable (deal/attack/defend/print/state)" << std::endl;
  return 0;
}