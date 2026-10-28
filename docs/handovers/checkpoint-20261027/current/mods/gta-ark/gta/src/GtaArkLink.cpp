// GTA side of the GTA -> ARK camera link (M1). Each game frame it writes GTA's final rendered
// camera and the player's pose to the GAL1 record (../../link-format.md). F7 toggles the link.
//
// Without GAL_WITH_SHV this builds a skeleton that loads and does nothing: there is no native
// access until a supported route exists. Do not install the skeleton build into the game.
#include <windows.h>
#include "camera_source.h"
#include "link_record.h"

namespace gal {

class Link {
public:
    explicit Link(std::unique_ptr<CameraSource> source) : source_(std::move(source)) {
        open_ = writer_.Open(DefaultPath());
        source_->Notify(open_ ? "ARK link: on (F7 toggles)" : "ARK link: cannot open the link file");
    }

    void Tick() {
        bool f7 = (GetAsyncKeyState(VK_F7) & 0x8000) != 0;
        if (f7 && !f7Held_) {
            enabled_ = !enabled_;
            source_->Notify(enabled_ ? "ARK link: on" : "ARK link: off");
        }
        f7Held_ = f7;
        CameraSample s{};
        if (!open_ || !source_->Sample(s)) return;
        Fields f{};
        for (int i = 0; i < 3; ++i) {
            f.camPos[i] = s.camPos[i];
            f.camRot[i] = s.camRot[i];
            f.playerPos[i] = s.playerPos[i];
        }
        f.fov = s.fov;
        f.heading = s.heading;
        f.flags = (s.storyMode ? kFlagStory : 0) | (enabled_ ? kFlagEnabled : 0);
        f.frame = ++frame_;
        writer_.Write(f);
    }

private:
    std::unique_ptr<CameraSource> source_;
    LinkWriter writer_;
    bool open_ = false, enabled_ = true, f7Held_ = false;
    uint64_t frame_ = 0;
};

}  // namespace gal

#ifdef GAL_WITH_SHV
#include <main.h>  // Script Hook V SDK: scriptRegister, scriptUnregister, scriptWait

static void ScriptMain() {
    gal::Link link(gal::MakeShvSource());
    for (;;) {
        link.Tick();
        scriptWait(0);
    }
}

BOOL APIENTRY DllMain(HMODULE module, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) scriptRegister(module, ScriptMain);
    else if (reason == DLL_PROCESS_DETACH) scriptUnregister(module);
    return TRUE;
}
#else
BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
#endif
