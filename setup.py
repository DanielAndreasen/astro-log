from setuptools import find_packages, setup

setup(
    name="astrolog",
    version="1.2.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    test_suite="tests",
    python_requires=">=3.10",
    install_requires=[
        "astropy",
        "astroquery",
        "bcrypt",
        "Flask>=2.3.2",
        "matplotlib",
        "mpld3",
        "numpy",
        "peewee>=3.15",
        "pygments>=2.15.1",
        "pytest",
        "setuptools>=68.0.0",
    ],
    author="Daniel Thaagaard Andreasen",
    license="MIT",
)
