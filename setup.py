from setuptools import setup, find_packages


setup(

    name='astrolog',
    version='0.0.1',

    packages=find_packages('src'),
    package_dir={'': 'src'},

    test_suite='tests',

    author='Daniel Thaagaard Andreasen',
    license='MIT'

)
