# This file is part of YOUR PROJECT NAME
# Copyright (C) CURRENT YEAR - Veos Digital
#

import sys
from setuptools import find_packages, setup
import pathlib

CURRENT_PYTHON_VERSION = sys.version_info[:2]
MIN_REQUIRED_PYTHON_VERSION = (3, 7)  # COMPATIBLE PYTHON VERSION
if CURRENT_PYTHON_VERSION < MIN_REQUIRED_PYTHON_VERSION:
    sys.stderr.write(
        """
==========================
Unsupported Python version
==========================
This version of YOUR PROJECT NAME requires Python {}.{}, but you're trying to
install it on Python {}.{}.
""".format(
            *(MIN_REQUIRED_PYTHON_VERSION + CURRENT_PYTHON_VERSION)
        )
    )
    sys.exit(1)

requirements = (pathlib.Path(__file__).parent / "requirements.txt").read_text().splitlines()
EXCLUDE_FROM_PACKAGES = []
print(requirements)
setup(
    name="YOUR PROJECT NAME",
    version="0.0.0-prealpha",
    python_requires=">={}.{}".format(*MIN_REQUIRED_PYTHON_VERSION),
    url="",
    author="",
    author_email="",
    description=(""),
    license="",
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    install_requires=requirements,
    entry_points={},
    zip_safe=False,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering" "Topic :: Scientific/Engineering :: Machine Learning",
        "Topic :: Scientific/Engineering :: Machine cognition",
    ],
)
