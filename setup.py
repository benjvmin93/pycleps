from setuptools import setup, find_packages

# Read the contents of the README file for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read the contents of requirements.txt for dependencies
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="pycleps",
    version="0.1.0",
    author="Benjamin",
    description="A tool to submit SLURM jobs to INRIA clusters using SSH.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/benjvmin93/pycleps",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pycleps=pycleps.main:app",
        ],
    },
)
