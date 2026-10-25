@echo off
rem Builds and runs the C++ record test, then builds GtaArkLink.asi with MSVC (x64).
rem Without SHV_SDK the ASI is a skeleton with no native access: do not install it.
rem With SHV_SDK=<Script Hook V SDK folder> it builds the Script Hook V camera source.
setlocal
set "HERE=%~dp0"
set "PATH=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer;%PATH%"
for /f "usebackq delims=" %%i in (`vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (echo MSVC C++ x64 tools not found; install the native_game_mods profile & exit /b 1)
call "%VSDIR%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
if not exist "%HERE%build" mkdir "%HERE%build"
cd /d "%HERE%build"

set "FLAGS=/nologo /std:c++17 /EHsc /W4 /WX /permissive- /DUNICODE /D_UNICODE"
cl %FLAGS% /Fe:gal_record_test.exe "%HERE%tests\gal_record_test.cpp" shell32.lib ole32.lib || exit /b 1
"%HERE%build\gal_record_test.exe" "%HERE%build\cpp_sample.bin" || exit /b 1

rem Compile-only check of the Script Hook V route against a stub of the SDK's declarations.
cl %FLAGS% /c /DGAL_WITH_SHV /I "%HERE%tests\shv_stub" /Fo:"%HERE%build\\" "%HERE%src\GtaArkLink.cpp" "%HERE%src\shv_source.cpp" >nul || (echo Script Hook V route failed to compile & exit /b 1)
echo Script Hook V route compiles ^(stub declarations, not linked^).

if defined SHV_SDK (
  cl %FLAGS% /LD /DGAL_WITH_SHV /I "%SHV_SDK%\inc" /Fe:GtaArkLink.asi "%HERE%src\GtaArkLink.cpp" "%HERE%src\shv_source.cpp" "%SHV_SDK%\lib\ScriptHookV.lib" user32.lib shell32.lib ole32.lib || exit /b 1
  echo Built GtaArkLink.asi with the Script Hook V camera source.
) else (
  cl %FLAGS% /LD /Fe:GtaArkLink.asi "%HERE%src\GtaArkLink.cpp" user32.lib shell32.lib ole32.lib || exit /b 1
  echo Built skeleton GtaArkLink.asi ^(no native access; not for installation^).
)
