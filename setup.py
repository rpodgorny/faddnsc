from setuptools import find_packages, setup

from faddns.version import __version__


setup(
    name="faddns",
    version=__version__,
    options={
        "build_exe": {"compressed": True, "include_files": ["etc/faddnsc.conf"]},
    },
    install_requires=["docopt"],
    scripts=["faddnsc"],
    packages=find_packages(),
)
