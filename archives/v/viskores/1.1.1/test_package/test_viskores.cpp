#include <viskores/Math.h>
#include <viskores/cont/Algorithm.h>
#include <viskores/cont/ArrayHandle.h>
#include <viskores/cont/Error.h>
#include <viskores/cont/ErrorBadValue.h>
#include <viskores/cont/Initialize.h>
#include <viskores/cont/Invoker.h>
#include <viskores/cont/RuntimeDeviceTracker.h>
#include <viskores/cont/serial/DeviceAdapterSerial.h>
#include <viskores/filter/contour/Contour.h>
#include <viskores/filter/entity_extraction/Threshold.h>
#include <viskores/io/VTKDataSetReader.h>
#include <viskores/io/VTKDataSetWriter.h>
#include <viskores/rendering/Actor.h>
#include <viskores/rendering/CanvasRayTracer.h>
#include <viskores/rendering/MapperRayTracer.h>
#include <viskores/rendering/Scene.h>
#include <viskores/rendering/View3D.h>
#include <viskores/source/Wavelet.h>
#include <viskores/worklet/WorkletMapField.h>

#include <cmath>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
int Passed = 0;

void Check(bool condition, const char* name)
{
  if (!condition)
    throw std::runtime_error(name);
  ++Passed;
  std::cout << "PASS " << name << '\n';
}

struct Square : viskores::worklet::WorkletMapField
{
  using ControlSignature = void(FieldIn, FieldOut);
  using ExecutionSignature = _2(_1);
  VISKORES_EXEC viskores::Int32 operator()(viskores::Int32 value) const
  {
    return value * value;
  }
};

void Run()
{
  viskores::cont::Initialize();
  viskores::cont::GetRuntimeDeviceTracker().ForceDevice(
    viskores::cont::DeviceAdapterTagSerial{});
  const std::vector<viskores::Int32> values{ 4, 1, 3, 2 };
  auto array = viskores::cont::make_ArrayHandle(values, viskores::CopyFlag::On);
  viskores::cont::Algorithm::Sort(array);
  auto sorted = array.ReadPortal();
  Check(sorted.Get(0) == 1 && sorted.Get(1) == 2 && sorted.Get(2) == 3 &&
          sorted.Get(3) == 4, "Serial sort");
  Check(viskores::cont::Algorithm::Reduce(array, viskores::Int32(0)) == 10,
        "Serial reduction");
  viskores::cont::ArrayHandle<viskores::Int32> scanned;
  const auto sum = viskores::cont::Algorithm::ScanExclusive(array, scanned);
  auto scan = scanned.ReadPortal();
  Check(sum == 10 && scan.Get(0) == 0 && scan.Get(1) == 1 && scan.Get(2) == 3 &&
          scan.Get(3) == 6, "Exclusive scan");
  viskores::cont::ArrayHandle<viskores::Int32> squared;
  viskores::cont::Invoker{}(Square{}, array, squared);
  auto square = squared.ReadPortal();
  Check(square.Get(0) == 1 && square.Get(1) == 4 && square.Get(2) == 9 &&
          square.Get(3) == 16, "Worklet dispatch");
  volatile viskores::Float32 dopA = 33962.035f, dopB = -30438.8f;
  volatile viskores::Float32 dopC = 41563.4f, dopD = -24871.969f;
  Check(viskores::FloatDistance(-0x1.2ca994p+6f,
          viskores::DifferenceOfProducts(dopA, dopB, dopC, dopD)) < 2,
        "Compensated product difference from binary32 inputs");
  volatile viskores::Float64 qa = 94906265.625, qb = -189812534.0, qc = 94906268.375;
  auto roots = viskores::QuadraticRoots(qa, qb, qc);
  Check(viskores::FloatDistance(1.0, roots[0]) < 3 &&
          viskores::FloatDistance(1.000000028975958, roots[1]) < 3,
        "Kahan quadratic with matching coefficient convention");

  auto volume = viskores::source::Wavelet{}.Execute();
  Check(volume.GetNumberOfPoints() == 9261 && volume.GetNumberOfCells() == 8000,
        "Wavelet structured volume");
  viskores::filter::contour::Contour contour;
  contour.SetActiveField("RTData");
  contour.SetIsoValue(0, 150.0);
  auto surface = contour.Execute(volume);
  Check(surface.GetNumberOfCells() > 0 && surface.GetNumberOfPoints() > 0 &&
          surface.HasPointField("RTData"), "Contour mesh and field mapping");

  viskores::filter::entity_extraction::Threshold threshold;
  threshold.SetActiveField("RTData");
  threshold.SetLowerThreshold(100.0);
  threshold.SetUpperThreshold(200.0);
  auto selected = threshold.Execute(volume);
  Check(selected.GetNumberOfCells() > 0 &&
          selected.GetNumberOfCells() < volume.GetNumberOfCells(), "Threshold selection");

  const char* vtkPath = "viskores-consumer.vtk";
  viskores::io::VTKDataSetWriter(vtkPath).WriteDataSet(surface);
  auto restored = viskores::io::VTKDataSetReader(vtkPath).ReadDataSet();
  const auto beforeBounds = surface.GetCoordinateSystem().GetBounds();
  const auto afterBounds = restored.GetCoordinateSystem().GetBounds();
  const viskores::Range beforeAxes[3] = { beforeBounds.X, beforeBounds.Y, beforeBounds.Z };
  const viskores::Range afterAxes[3] = { afterBounds.X, afterBounds.Y, afterBounds.Z };
  bool coordinatesMatch = true;
  for (int axis = 0; axis < 3; ++axis)
  {
    coordinatesMatch = coordinatesMatch &&
      std::fabs(beforeAxes[axis].Min - afterAxes[axis].Min) < 1e-4 &&
      std::fabs(beforeAxes[axis].Max - afterAxes[axis].Max) < 1e-4;
  }
  const auto beforeRange = surface.GetPointField("RTData").GetRange().ReadPortal().Get(0);
  const auto afterRange = restored.GetPointField("RTData").GetRange().ReadPortal().Get(0);
  Check(restored.GetNumberOfCells() == surface.GetNumberOfCells() &&
          restored.GetNumberOfPoints() == surface.GetNumberOfPoints() &&
          restored.HasPointField("RTData") && coordinatesMatch &&
          std::fabs(beforeRange.Min - afterRange.Min) < 1e-3 &&
          std::fabs(beforeRange.Max - afterRange.Max) < 1e-3, "VTK data roundtrip");
  std::remove(vtkPath);

  bool rejected = false;
  try
  {
    contour.SetActiveField("missing-consumer-field");
    contour.Execute(volume);
  }
  catch (const viskores::cont::ErrorBadValue& error)
  {
    rejected = error.GetMessage().find("missing-consumer-field") != std::string::npos;
  }
  Check(rejected, "Missing field rejection");

  viskores::rendering::Scene scene;
  scene.AddActor(viskores::rendering::Actor(surface.GetCellSet(),
    surface.GetCoordinateSystem(), surface.GetPointField("RTData"),
    viskores::cont::ColorTable("inferno")));
  viskores::rendering::MapperRayTracer mapper;
  viskores::rendering::CanvasRayTracer canvas(64, 64);
  viskores::rendering::View3D view(scene, mapper, canvas);
  view.SetWorldAnnotationsEnabled(false);
  view.SetRenderAnnotationsEnabled(false);
  view.GetCamera().ResetToBounds(surface.GetCoordinateSystem().GetBounds());
  view.Paint();
  auto pixels = view.GetCanvas().GetColorBuffer().ReadPortal();
  viskores::Id colored = 0;
  bool finite = true;
  for (viskores::Id i = 0; i < pixels.GetNumberOfValues(); ++i)
  {
    auto pixel = pixels.Get(i);
    for (int channel = 0; channel < 4; ++channel)
      finite = finite && std::isfinite(pixel[channel]);
    colored += (pixel[0] > 0.01f || pixel[1] > 0.01f || pixel[2] > 0.01f);
  }
  Check(pixels.GetNumberOfValues() == 4096 && finite && colored > 100 && colored < 4096,
        "Software ray-tracing pixel readback");
  const char* pngPath = "viskores-consumer.png";
  view.SaveAs(pngPath);
  std::ifstream png(pngPath, std::ios::binary);
  unsigned char signature[8]{};
  png.read(reinterpret_cast<char*>(signature), 8);
  Check(png.gcount() == 8 && signature[0] == 137 && signature[1] == 'P' &&
          signature[2] == 'N' && signature[3] == 'G' && signature[4] == 13 &&
          signature[5] == 10 && signature[6] == 26 && signature[7] == 10,
        "PNG encoder signature");
  png.close();
  std::remove(pngPath);
}
}

int main()
{
  try
  {
    Run();
    std::cout << "CONSUMER_RESULT=" << Passed << "/13\n";
    return Passed == 13 ? 0 : 1;
  }
  catch (const std::exception& error)
  {
    std::cerr << "FAIL after " << Passed << " checks: " << error.what() << '\n';
    return 1;
  }
}
