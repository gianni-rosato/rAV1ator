from setuptools import setup, find_packages

setup(
    name='rAV1ator',
    version='2.0.0',
    description='AV1 Hypertuning GUI',
    author='Gianni Rosato',
    author_email='grosatowork@proton.me',
    packages=find_packages(),
    package_data={'': ['window.ui']},
    include_package_data=True,
    classifiers=[],
    install_requires=[],
)
