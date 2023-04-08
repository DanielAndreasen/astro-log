from setuptools import find_packages, setup

setup(
    name='astrolog',
    version='0.0.1',

    packages=find_packages('src'),
    package_dir={'': 'src'},

    test_suite='tests',

    python_requires='>=3.10',

    install_requires=[
        'Flask >= 2.2',
        'peewee >= 3.15',
        'bcrypt'
    ],

    author='Daniel Thaagaard Andreasen',
    license='MIT'
)
