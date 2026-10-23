// SPDX-License-Identifier: MIT
// Copyright (c) 2026 openswx contributors
#include <charconv>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <string_view>
#include <system_error>

#include "openswstep/export.h"

namespace {
bool ReadIndex(std::string_view text, uint64_t& value) {
  const auto parsed =
      std::from_chars(text.data(), text.data() + text.size(), value);
  return parsed.ec == std::errc{} && parsed.ptr == text.data() + text.size();
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 5) {
    std::cerr << "Usage: case_export <captured.sldprt> <payload-index> "
                 "<body-id> <output.step>\n";
    return 1;
  }
  uint64_t payload = 0;
  uint64_t body = 0;
  if (!ReadIndex(argv[2], payload) || !ReadIndex(argv[3], body) || body == 0 ||
      payload > std::numeric_limits<std::size_t>::max()) {
    std::cerr << "Invalid explicit payload/body selection\n";
    return 1;
  }
  // Initial captured fixtures have independently verified metre coordinates.
  // This driver neither selects a configuration nor resolves delta history.
  openswstep::ExportOptions options;
  options.length_unit = openswstep::LengthUnit::kMetre;
  options.tolerance = 1e-8;
  const auto step = openswstep::ExportSolidWorksFile(
      std::filesystem::path(argv[1]), static_cast<std::size_t>(payload),
      openparasolid::NodeId{body}, options);
  if (!step.ok()) {
    std::cerr << "Export failed at " << step.error().offset << ": "
              << step.error().message << '\n';
    return 2;
  }
  const auto written =
      openswstep::WriteStepFile(step.value(), std::filesystem::path(argv[4]));
  if (!written.ok()) {
    std::cerr << written.error().message << '\n';
    return 3;
  }
  const auto& counts = step.value().statistics;
  std::cout << "{\"faces\":" << counts.faces << ",\"edges\":" << counts.edges
            << ",\"vertices\":" << counts.vertices
            << ",\"shells\":" << counts.shells
            << ",\"solids\":" << counts.solids << "}\n";
  return 0;
}
