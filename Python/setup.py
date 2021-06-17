import setuptools

from Whittler.classes.Metadata import WHITTLER_VERSION

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name='Whittler',
    scripts=['Whittler/Whittler.py'],
    packages=setuptools.find_packages(),
    version=WHITTLER_VERSION,
    license='MIT',
    description="A machine-learning-capable modular shell for reducing large datasets (especially code static analysis tool outputs)",
    author="Ben Ege Izmirli",
    author_email="benegegalaxy@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BenEgeIzmirli/Whittler",
    download_url=f"https://github.com/BenEgeIzmirli/Whittler/archive/{WHITTLER_VERSION}.tar.gz",
    # keywords = [], # TODO
    install_requires = [
        'numpy'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "Topic :: Database",
        "Topic :: Utilities",
        "Topic :: Text Processing :: Linguistic"
    ],
)