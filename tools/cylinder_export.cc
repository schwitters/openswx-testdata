// SPDX-License-Identifier: MIT
// Copyright (c) 2026 openswx contributors
#include <filesystem>
#include <iostream>

#include "openswstep/export.h"

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "Usage: cylinder_export <captured.sldprt> <output.step>\n";
    return 1;
  }
  // These identities belong only to part-cylinder-001's frozen source bytes.
  // This checks an explicit partition; it does not resolve delta history.
  constexpr std::size_t kCapturedPartitionIndex = 0;
  constexpr openparasolid::NodeId kCapturedBody{2};
  openswstep::ExportOptions options;
  options.length_unit = openswstep::LengthUnit::kMetre;
  options.tolerance = 1e-8;
  const auto step = openswstep::ExportSolidWorksFile(
      std::filesystem::path(argv[1]), kCapturedPartitionIndex, kCapturedBody,
      options);
  if (!step.ok()) {
    std::cerr << "Export failed at " << step.error().offset << ": "
              << step.error().message << '\n';
    return 2;
  }
  const auto& counts = step.value().statistics;
  if (counts.faces != 3 || counts.edges != 2 || counts.solids != 1 ||
      counts.shells != 1) {
    std::cerr << "Captured cylinder topology was not preserved\n";
    return 3;
  }
  const auto written =
      openswstep::WriteStepFile(step.value(), std::filesystem::path(argv[2]));
  if (!written.ok()) {
    std::cerr << written.error().message << '\n';
    return 4;
  }
  std::cout << "{\"faces\":" << counts.faces << ",\"edges\":" << counts.edges
            << ",\"vertices\":" << counts.vertices
            << ",\"shells\":" << counts.shells
            << ",\"solids\":" << counts.solids << "}\n";
  return 0;
}
