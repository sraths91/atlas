"""
Setup script for Atlas
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="atlas",
    version="1.0.0",
    author="Atlas Contributors",
    description="Enhanced system monitor for Turing Atlas on macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/atlas",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS :: MacOS X",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "atlas=atlas.app:main",
            "atlas-menubar=atlas.menubar_app:main",
            "atlas-editor=atlas.web_editor:main",
        ],
    },
)
