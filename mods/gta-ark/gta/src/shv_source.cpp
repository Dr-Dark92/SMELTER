// Script Hook V camera source. Compiled only with GAL_WITH_SHV and the Script Hook V SDK
// (SHV_SDK), because Script Hook V does not yet support the installed Enhanced build.
#ifdef GAL_WITH_SHV
#include "camera_source.h"
#include "natives.h"
#include <windows.h>
#include <main.h>  // Script Hook V SDK: nativeInit, nativePush64, nativeCall

namespace gal {
namespace {

// Script Hook V returns Vector3 with each float padded to 8 bytes.
struct ShvVector3 {
    float x; DWORD padX;
    float y; DWORD padY;
    float z; DWORD padZ;
};

template <typename T>
UINT64 Arg(T value) {
    UINT64 raw = 0;
    static_assert(sizeof(T) <= sizeof raw, "native arguments are at most 64 bits");
    memcpy(&raw, &value, sizeof(T));
    return raw;
}

template <typename R, typename... A>
R Invoke(UINT64 hash, A... args) {
    nativeInit(hash);
    (nativePush64(Arg(args)), ...);
    return *reinterpret_cast<R*>(nativeCall());
}

class ShvSource final : public CameraSource {
public:
    bool Sample(CameraSample& out) override {
        ShvVector3 cam = Invoke<ShvVector3>(natives::GET_FINAL_RENDERED_CAM_COORD);
        ShvVector3 rot = Invoke<ShvVector3>(natives::GET_FINAL_RENDERED_CAM_ROT, 2);
        int ped = Invoke<int>(natives::PLAYER_PED_ID);
        ShvVector3 feet = Invoke<ShvVector3>(natives::GET_ENTITY_COORDS, ped, TRUE);
        out = {{cam.x, cam.y, cam.z}, {rot.x, rot.y, rot.z}, Invoke<float>(natives::GET_FINAL_RENDERED_CAM_FOV),
               {feet.x, feet.y, feet.z}, Invoke<float>(natives::GET_ENTITY_HEADING, ped),
               true};  // Script Hook V runs only in Story Mode and closes the game online.
        return true;
    }

    void Notify(const char* text) override {
        Invoke<int>(natives::BEGIN_TEXT_COMMAND_THEFEED_POST, "STRING");
        Invoke<int>(natives::ADD_TEXT_COMPONENT_SUBSTRING_PLAYER_NAME, text);
        Invoke<int>(natives::END_TEXT_COMMAND_THEFEED_POST_TICKER, FALSE, TRUE);
    }
};

}  // namespace

std::unique_ptr<CameraSource> MakeShvSource() { return std::make_unique<ShvSource>(); }

}  // namespace gal
#endif
