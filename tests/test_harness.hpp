/**
 * @file test_harness.hpp
 * @brief Supplies a dependency-free test registry and assertion helpers for the
 * workbench.
 * @details Exact declarations and line locations are generated in
 * docs/generated/symbol-index.md.
 */

#pragma once

#include <cstddef>
#include <functional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace imlp::test {

using TestFunction = void (*)();

/** Associates a stable test name with its function. */
struct TestCase {
  std::string name;
  TestFunction function;
};

/** Return the process-wide registry populated before main. */
inline std::vector<TestCase>& registry() {
  static std::vector<TestCase> tests;
  return tests;
}

/** Register one test function during static initialization. */
class Registrar {
 public:
  Registrar(std::string name, const TestFunction function) {
    registry().push_back({std::move(name), function});
  }
};

/** Report a failed boolean expression with source location. */
inline void expect(const bool condition, const std::string_view expression,
                   const std::string_view file, const int line) {
  if (!condition) {
    throw std::runtime_error(std::string(file) + ":" + std::to_string(line) +
                             " expectation failed: " + std::string(expression));
  }
}

/** Compare values without requiring a stream insertion operator. */
template <typename Left, typename Right>
void expect_equal(const Left& left, const Right& right, const std::string_view expression,
                  const std::string_view file, const int line) {
  expect(left == right, expression, file, line);
}

}  // namespace imlp::test

#define IMLP_TEST(name)                                  \
  static void name();                                    \
  static const ::imlp::test::Registrar name##_registrar{ \
      #name,                                             \
      &name,                                             \
  };                                                     \
  static void name()

#define IMLP_EXPECT(expression) \
  ::imlp::test::expect(static_cast<bool>(expression), #expression, __FILE__, __LINE__)

#define IMLP_EXPECT_EQ(left, right) \
  ::imlp::test::expect_equal((left), (right), #left " == " #right, __FILE__, __LINE__)
