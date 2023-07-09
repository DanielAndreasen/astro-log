from setuptools import find_packages, setup

setup(
    name="astrolog",
    version="1.2.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    test_suite="tests",
    python_requires=">=3.10",
    install_requires=[
        "astropy >= 5.3.1",
        "bcrypt",
        "Flask >= 2.2",
        "matplotlib >= 3.7.2",
        "mpld3 >= 0.5.9",
        "numpy => 1.25.0",
        "peewee >= 3.15",
        "pytest",
    ],
    author="Daniel Thaagaard Andreasen",
    license="MIT",
)
