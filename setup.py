from setuptools import find_packages, setup

setup(
    name='astrolog',
    version='1.0.0',

    packages=find_packages('src'),
    package_dir={'': 'src'},

    test_suite='tests',

    python_requires='>=3.10',

    install_requires=[
        'Flask >= 2.2',
        'peewee >= 3.15',
        'pytest',
        'bcrypt'
    ],

    author='Daniel Thaagaard Andreasen',
    license='MIT'
)
