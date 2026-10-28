// Where the GTA camera comes from. The link logic depends only on this interface, so the
// native route (Script Hook V, or the Ultimate ASI Loader route) can change without touching it.
#pragma once
#include <memory>

namespace gal {

struct CameraSample {
    float camPos[3];
    float camRot[3];  // pitch, roll, yaw (rotation order 2), degrees
    float fov;
    float playerPos[3];
    float heading;
    bool storyMode;
};

class CameraSource {
public:
    virtual ~CameraSource() = default;
    // False when no sample is available (for example on the landing page).
    virtual bool Sample(CameraSample& out) = 0;
    virtual void Notify(const char* text) = 0;
};

#ifdef GAL_WITH_SHV
std::unique_ptr<CameraSource> MakeShvSource();  // shv_source.cpp
#endif

}  // namespace gal
