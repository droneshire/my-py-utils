from setuptools import find_packages, setup

required = []
with open("requirements.txt", encoding="utf-8") as infile:
    required = infile.read().splitlines()

setup(
    name="ryutils",
    version="1.0.0",
    description="A collection of utilities for Python",
    long_description=(
        "Random assortment of various utilities for Python"
        "that I have put together over the years"
    ),
    author="Ross Yeager",
    author_email="ryeager12@email.com",
    packages=find_packages(),
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
