/**
 * @file test_main.cpp
 * @brief Runs the registered test suite and prints a compact deterministic
 * summary.
 * @details The entry point and significant variable locations are indexed in
 * the generated symbol index.
 */

#include <exception>
#include <iostream>

#include "test_harness.hpp"

/** Execute every registered test and return failure when any assertion throws.
 */
int main() {
  std::size_t passed = 0;
  std::size_t failed = 0;
  for (const auto& test : imlp::test::registry()) {
    try {
      test.function();
      ++passed;
      std::cout << "PASS " << test.name << '\n';
    } catch (const std::exception& error) {
      ++failed;
      std::cerr << "FAIL " << test.name << ": " << error.what() << '\n';
    } catch (...) {
      ++failed;
      std::cerr << "FAIL " << test.name << ": unknown exception\n";
    }
  }
  std::cout << "SUMMARY passed=" << passed << " failed=" << failed << '\n';
  return failed == 0U ? 0 : 1;
}
