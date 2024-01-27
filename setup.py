from setuptools import find_packages, setup

required = []
with open("requirements.txt", encoding="utf-8") as infile:
    required = infile.read().splitlines()

LONG_DESCRIPTION = ""
with open("README.md", encoding="utf-8") as infile:
    LONG_DESCRIPTION = infile.read()

VERSION = "0.0.0"
with open("VERSION", encoding="utf-8") as infile:
    VERSION = infile.read().strip()

setup(
    name="ryutils",
    version=VERSION,
    description="A collection of utilities for Python",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Ross Yeager",
    author_email="ryeager12@email.com",
    packages=find_packages(include=["ryutils", "ryutils.*"]),
    package_data={"ryutils": ["py.typed"]},
    install_requires=required,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
