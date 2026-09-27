# Shared paths (packaged version).
# HACK_DATA: folder with the raw hackathon files (C1_/C2_Phenotype_Data_V2.csv, the four genotype zips,
#            environmental_features.csv). Default: ./data next to this file.
# HACK_CACHE: where derived files are written. Default: ./cache next to this file.
import os
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get('HACK_DATA', os.path.join(HERE, 'data'))
S = os.environ.get('HACK_CACHE', os.path.join(HERE, 'cache'))
os.makedirs(f'{S}/exploration', exist_ok=True)
os.makedirs(f'{S}/geno', exist_ok=True)
