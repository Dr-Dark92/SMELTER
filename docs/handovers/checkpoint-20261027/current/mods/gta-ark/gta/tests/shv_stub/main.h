// Compile-check stub: declarations matching the Script Hook V SDK's main.h functions used by
// the link. Used only by build.bat's compile-only step (/c); never linked, never shipped.
// The real SDK replaces this via SHV_SDK.
#pragma once
#include <windows.h>

void scriptRegister(HMODULE module, void (*scriptMain)());
void scriptUnregister(HMODULE module);
void scriptWait(DWORD time);
void nativeInit(UINT64 hash);
void nativePush64(UINT64 value);
PUINT64 nativeCall();
