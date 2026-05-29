from setuptools import find_packages, setup

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="smart_cs",
    version="0.1.0",
    description="Universal intelligent customer service base.",
    long_description=open("README.md", "r", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=("tests", "tests.*", "examples", "examples.*")),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "smart-cs=smart_cs.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
