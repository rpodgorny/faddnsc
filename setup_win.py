from cx_Freeze import setup, Executable

from faddns.version import __version__

base = "Win32GUI"

setup(
    name="faddns",
    version=__version__,
    options={
        "build_exe": {
            "includes": [
                "re",
            ],
            "include_msvcr": True,
        },
    },
    executables=[
        Executable(script="faddnsc"),
        # Executable(script='faddnsc_gui'),
    ],
)
