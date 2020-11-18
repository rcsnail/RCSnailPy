import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="RCSnailPy",
    version="0.0.4",
    author="Rainer Paat",
    author_email="rainer@rcsnail.ee",
    description="RCSnail API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rcsnail/RCSnailPy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
        "aiortc",
        "pirebase",
        "FirebaseData",
    ]
)