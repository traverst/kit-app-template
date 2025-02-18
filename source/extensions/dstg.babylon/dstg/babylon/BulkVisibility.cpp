#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/imageable.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/sdf/path.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;
using namespace pxr;

// Function to batch update prim visibility
void batchSetVisibility(const std::string& usdPath,
                        const std::vector<std::string>& primPaths,
                        bool visible) {
    UsdStageRefPtr stage = UsdStage::Open(usdPath);
    if (!stage) {
        throw std::runtime_error("Failed to open USD stage.");
    }

    TfToken visibilityToken = visible ? UsdGeomTokens->inherited : UsdGeomTokens->invisible;

    for (const auto& path : primPaths) {
        UsdPrim prim = stage->GetPrimAtPath(SdfPath(path));
        if (!prim) continue;

        UsdGeomImageable imageable(prim);
        if (!imageable) continue;

        imageable.GetVisibilityAttr().Set(visibilityToken, stage->GetSessionLayer()->GetPseudoRoot());
    }

    // No need to save the stage since we are using the session layer
}

PYBIND11_MODULE(usd_visibility, m) {
    m.def("batch_set_visibility", &batchSetVisibility,
          py::arg("usdPath"), py::arg("primPaths"), py::arg("visible"));
}


// import usd_visibility

// # Generate 81k prim paths
// prim_paths = [f"/World/Prim_{i}" for i in range(81000)]

// # Set visibility (False = invisible, True = visible)
// usd_visibility.batch_set_visibility("scene.usda", prim_paths, False)
