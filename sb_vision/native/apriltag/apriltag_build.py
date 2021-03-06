"""
CFFI build script for AprilTags library and integration.

This is how we actually do the fiducial marker detection.
"""

from pathlib import Path

from cffi import FFI

ffi = FFI()


base = Path(__file__).parent

source_files = [
    x
    for x in base.glob("contrib/april/**/*.c")
    if x.stem not in (
        'tag16h5',
        'tag25h7',
        'tag25h9',
        'tag36artoolkit',
        'tag36h10',
    )
]

with (base / 'apriltag_interface.c').open('r') as apriltag_interface:
    ffi.set_source(
        "sb_vision.native.apriltag._apriltag",
        apriltag_interface.read(),
        include_dirs=[
            str(base),
            str(base / 'contrib' / 'april'),
            str(base / 'contrib' / 'april' / 'common'),
        ],
        sources=[str(x) for x in source_files],
        extra_compile_args=['-std=c11'],
    )

# Define the functions to be used.

with (base / 'apriltag_cdefs.h').open('r') as apriltag_interface_h:
    ffi.cdef(apriltag_interface_h.read())

if __name__ == "__main__":
    ffi.compile(verbose=True)
