// GAL1 link record writer (see ../../link-format.md). Header-only, Win32 file I/O, no exceptions.
#pragma once
#include <windows.h>
#include <shlobj.h>
#include <cstddef>
#include <cstdint>
#include <string>

namespace gal {

constexpr DWORD kRecordSize = 64;
constexpr uint32_t kFlagStory = 1;
constexpr uint32_t kFlagEnabled = 2;

#pragma pack(push, 1)
struct Fields {  // file offsets 8..63
    float camPos[3];
    float camRot[3];  // pitch, roll, yaw (GTA rotation order 2), degrees
    float fov;
    float playerPos[3];
    float heading;
    uint32_t flags;
    uint64_t frame;
};
#pragma pack(pop)
static_assert(sizeof(Fields) == kRecordSize - 8, "GAL1 fields must fill offsets 8..63");
static_assert(8 + offsetof(Fields, fov) == 32 && 8 + offsetof(Fields, heading) == 48 &&
              8 + offsetof(Fields, flags) == 52 && 8 + offsetof(Fields, frame) == 56,
              "GAL1 offsets must match link-format.md");

// %LOCALAPPDATA%\SMELTER\gta-ark-link\camera.bin
inline std::wstring DefaultPath() {
    wchar_t* base = nullptr;
    std::wstring path;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, 0, nullptr, &base))) path = base;
    CoTaskMemFree(base);
    return path.empty() ? std::wstring() : path + L"\\SMELTER\\gta-ark-link\\camera.bin";
}

// Seqlock writer: odd sequence while writing, even when complete; the file is never truncated.
class LinkWriter {
public:
    LinkWriter() = default;
    LinkWriter(const LinkWriter&) = delete;
    LinkWriter& operator=(const LinkWriter&) = delete;
    ~LinkWriter() { Close(); }

    bool Open(const std::wstring& path) {
        Close();
        if (path.empty()) return false;
        std::wstring folder = path.substr(0, path.find_last_of(L'\\'));
        int made = SHCreateDirectoryExW(nullptr, folder.c_str(), nullptr);
        if (made != ERROR_SUCCESS && made != ERROR_ALREADY_EXISTS && made != ERROR_FILE_EXISTS) return false;
        file_ = CreateFileW(path.c_str(), GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE,
                            nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file_ == INVALID_HANDLE_VALUE) return false;
        unsigned char head[8] = {};
        LARGE_INTEGER size{};
        if (GetFileSizeEx(file_, &size) && size.QuadPart == kRecordSize && ReadAt(0, head, sizeof head) &&
            memcmp(head, "GAL1", 4) == 0) {
            memcpy(&sequence_, head + 4, 4);
            sequence_ &= ~1u;
            return true;
        }
        unsigned char blank[kRecordSize] = {'G', 'A', 'L', '1'};
        sequence_ = 0;
        return WriteAt(0, blank, kRecordSize) && SetEndOfFile(file_);
    }

    bool Write(const Fields& fields) {
        if (file_ == INVALID_HANDLE_VALUE) return false;
        uint32_t busy = sequence_ + 1, done = sequence_ + 2;
        if (!WriteAt(4, &busy, 4) || !WriteAt(8, &fields, sizeof fields) || !WriteAt(4, &done, 4)) return false;
        sequence_ = done;
        return true;
    }

    uint32_t Sequence() const { return sequence_; }

    void Close() {
        if (file_ != INVALID_HANDLE_VALUE) CloseHandle(file_);
        file_ = INVALID_HANDLE_VALUE;
    }

private:
    bool WriteAt(DWORD offset, const void* data, DWORD size) {
        OVERLAPPED at{};
        at.Offset = offset;
        DWORD written = 0;
        return WriteFile(file_, data, size, &written, &at) && written == size;
    }
    bool ReadAt(DWORD offset, void* data, DWORD size) {
        OVERLAPPED at{};
        at.Offset = offset;
        DWORD read = 0;
        return ReadFile(file_, data, size, &read, &at) && read == size;
    }

    HANDLE file_ = INVALID_HANDLE_VALUE;
    uint32_t sequence_ = 0;
};

}  // namespace gal
