// GTA V natives used by the link, by hash. Names/hashes follow alloc8or's native DB
// (github.com/alloc8or/gta5-nativedb-data). VERIFY each hash against that DB before the
// first in-game run: they are written from the DB's naming and have not run in Enhanced yet.
#pragma once
#include <cstdint>

namespace gal::natives {

constexpr uint64_t PLAYER_PED_ID = 0xD80958FC74E988A6;                 // () -> Ped
constexpr uint64_t GET_ENTITY_COORDS = 0x3FEF770D40960D5A;             // (Entity, BOOL alive) -> Vector3
constexpr uint64_t GET_ENTITY_HEADING = 0xE83D4F9BA2A38914;            // (Entity) -> float
constexpr uint64_t GET_FINAL_RENDERED_CAM_COORD = 0xA200EB1EE790F448;  // () -> Vector3
constexpr uint64_t GET_FINAL_RENDERED_CAM_ROT = 0x5B4E4C817FCC2DFB;    // (int rotationOrder) -> Vector3
constexpr uint64_t GET_FINAL_RENDERED_CAM_FOV = 0x80EC114669DAEFF4;    // () -> float
constexpr uint64_t BEGIN_TEXT_COMMAND_THEFEED_POST = 0x202709F4C58A0424;          // (const char* textLabel)
constexpr uint64_t ADD_TEXT_COMPONENT_SUBSTRING_PLAYER_NAME = 0x6C188BE134E074AA;  // (const char* text)
constexpr uint64_t END_TEXT_COMMAND_THEFEED_POST_TICKER = 0x2ED7843F8F801023;     // (BOOL blink, BOOL showInBrief) -> int

}  // namespace gal::natives
