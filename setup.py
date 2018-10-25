from setuptools import setup

setup(
    name='meson-cmake-wrapper',
    version='0.1.4',
    description='Build system wrapper that provides Meson integration in CMake IDE\'s',
    author='Niclas Moeslund Overby',
    author_email='noverby@prozum.dk',
    url='http://github.com/prozum/meson-cmake-wrapper',
    packages=['mcw'],
    entry_points={'console_scripts': ['meson-cmake-wrapper=mcw.main:main', 'mcw=mcw.main:main']},
    license='MIT license',
    python_requires='>=3.5',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown"
)
