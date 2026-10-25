# CLI-only mod toolchain: portable tests, Lua tests, and Windows cross-compilation.
# Pin both the reviewed base and direct package versions; runtime selects an image ID.
FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4
RUN apk add --no-cache g++=15.2.0-r5 lua5.4=5.4.8-r0 mingw-w64-gcc=15.2.0-r0 \
    && apk info -v > /opt/smelter-toolchain-packages.txt
WORKDIR /workspace
USER 65534:65534
