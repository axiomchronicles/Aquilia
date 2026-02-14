#!/usr/bin/env python3
"""
Setup script for Aquilia framework.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="aquilia",
    version="0.2.0",
    description="Async-native Python web framework with flow-first routing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Aquilia Contributors",
    url="https://github.com/yourusername/aquilia",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "docs"]),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=requirements + [
        "uvicorn>=0.30.0",
        "python-dotenv>=1.0.0",
        "jinja2>=3.1.0",
        "cryptography>=41.0.0",
        "argon2-cffi>=23.1.0",
        "passlib>=1.7.4",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "httpx>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aq=aquilia.cli.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    keywords="web framework async asgi http api",
    project_urls={
        "Documentation": "https://github.com/yourusername/aquilia/docs",
        "Source": "https://github.com/yourusername/aquilia",
        "Issues": "https://github.com/yourusername/aquilia/issues",
    },
)
