// C++ writer checks, plus a sample file that tests/test_link.py reads with the Python reader.
// Usage: gal_record_test.exe <sample-path>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <filesystem>
#include <iterator>
#include <vector>
#include "../src/link_record.h"

static int failures = 0;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); ++failures; } } while (0)

static std::vector<unsigned char> ReadAll(const wchar_t* path) {
    std::ifstream in(std::filesystem::path(path), std::ios::binary);
    return {std::istreambuf_iterator<char>(in), {}};
}

int wmain(int argc, wchar_t** argv) {
    if (argc != 2) { std::printf("usage: gal_record_test <sample-path>\n"); return 2; }
    const wchar_t* path = argv[1];
    DeleteFileW(path);

    gal::Fields f{{1, 2, 3}, {10, 0, 45}, 50, {4, 5, 6}, 90, 3, 7};
    {
        gal::LinkWriter w;
        CHECK(w.Open(path));
        CHECK(w.Write(f));
        CHECK(w.Sequence() == 2);
    }
    std::vector<unsigned char> raw = ReadAll(path);
    CHECK(raw.size() == gal::kRecordSize);
    if (raw.size() == gal::kRecordSize) {
        uint32_t seq; float fov, heading; uint32_t flags; uint64_t frame;
        std::memcpy(&seq, &raw[4], 4); std::memcpy(&fov, &raw[32], 4); std::memcpy(&heading, &raw[48], 4);
        std::memcpy(&flags, &raw[52], 4); std::memcpy(&frame, &raw[56], 8);
        CHECK(std::memcmp(raw.data(), "GAL1", 4) == 0);
        CHECK(seq == 2 && fov == 50 && heading == 90 && flags == 3 && frame == 7);
    }
    {
        gal::LinkWriter again;  // reopening continues the sequence and keeps the size
        CHECK(again.Open(path));
        CHECK(again.Sequence() == 2);
        CHECK(again.Write(f));
        CHECK(again.Sequence() == 4);
    }
    CHECK(ReadAll(path).size() == gal::kRecordSize);
    {
        gal::LinkWriter last;  // leave the sample with sequence 6 for the Python reader
        CHECK(last.Open(path) && last.Write(f));
    }
    std::printf(failures ? "gal_record_test: %d failure(s)\n" : "gal_record_test: OK\n", failures);
    return failures ? 1 : 0;
}
