from setuptools import find_packages, setup

setup(
    name="sigplane",
    version="1.0.0",
    description="Signal Planespotter",
    url="https://github.com/sehaas/sigplane",
    author="Sebastian Haas",
    author_email="sehaas@deebas.com",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "pysignald @ git+https://gitlab.com/stavros/pysignald.git",
        "PyYAML",
    ],
)
