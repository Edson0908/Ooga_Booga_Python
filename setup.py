from setuptools import setup, find_packages
from pathlib import Path

VERSION = '0.0.4'
DESCRIPTION = "A Python wrapper for the Ooga Booga API, providing seamless integration with Berachain liquidity for DApps and protocols."
long_description = (Path(__file__).parent / "README.md").read_text()

# Read dependencies from requirements.txt
requirements = (Path(__file__).parent / "requirements.txt").read_text().splitlines()

# Setting up
setup(
    name="Ooga_Booga_Python",
    version=VERSION,
    author="1220.moritz",
    url='https://github.com/1220moritz/Ooga_Booga_Python',
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    license_files=('LICENSE.txt',),
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['requirements.txt']},
    install_requires=requirements,
    keywords=['berachain', 'dex', 'api-wrapper', 'blockchain', 'ooga-booga'],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires='>=3.9',
)
