from setuptools import setup, find_packages

setup(
    name="eml-analyzer",
    version="0.1.0",
    description="A CLI tool for analyzing local EML files",
    author="Your Name",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "email-validator>=1.1.0",
    ],
    entry_points={
        "console_scripts": [
            "eml-analyzer=eml_analyzer.cli:main",
        ],
    },
)
