from setuptools import setup, find_packages, find_namespace_packages
packages = find_packages("src") + find_packages("EVRPTW_Core") + find_packages("EVRPTW_Dataset_Generator/src")
packages += find_namespace_packages(".", include=["EVRPTW_Benchmark*"], exclude=["*.tests*"])
setup(packages=packages, package_dir={"evrptw_db": "src/evrptw_db", "evrptw_core": "EVRPTW_Core/evrptw_core", "evrptw_stage2": "EVRPTW_Dataset_Generator/src/evrptw_stage2", "evrptw_cle": "EVRPTW_Dataset_Generator/src/evrptw_cle"}, include_package_data=True)
