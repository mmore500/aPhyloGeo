from setuptools import find_packages, setup

setup(
    name="aphylogeo",
    url="https://github.com/tahiri-lab/aPhyloGeo",
    author="Tahiri Lab",
    description="A phylogenetic and geographic analysis tool",
    version="0.0.1",
    include_package_data=True,
    install_requires=[
        "numpy>=1.25.2",
        "pandas>=1.3.5",
        "bio>=1.5.2",
        "multiprocess>=0.70.14",
        "psutil>=5.9.4",
        "PyYAML>=6.0",
        "pytest>=7.2.1",
    ],
    python_requires=">=3.9.0,<=3.11.1",
    packages=find_packages(),
)
