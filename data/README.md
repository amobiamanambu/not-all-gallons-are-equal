# Data structure

`input/` contains only frozen machine-readable evidence used by the manuscript workflow. `analysis_ready/` is rebuilt by `analysis/01_prepare_analysis_data.py`; it adds row-level source identifiers, URLs, locators, status fields, and declared transformations. The analysis does not fetch live data, so later changes to provider webpages cannot silently alter the results.

The Google input contains 97 named location-years used by the manuscript plus four aggregate rows retained for the documented FY2024 quality-control check. Meta contains 70 U.S. facility-years, AWS contains four matched U.S. regions, and the Aqueduct input contains the 26 U.S. locations used in Figure 3. The USGS input contains 32,874 daily observations: 10,958 observations for each of three stations used in Figure 6 and Table 4, with the Council Bluffs series also used in Figure 8. The Mesa source extract is retained because it is transformed into the 2,676 complete daily records and 66 monthly observations used in Figure 8.

The full Aqueduct 4.0 distribution and large provider reports are not duplicated here. Their official locations, version information, exact report pages, and archived-file hashes are recorded in `../metadata/source_register.csv`. The 26-location U.S. analysis-ready Aqueduct join needed to reproduce Figure 3 is included.

The City of Mesa raw CSV is public data and is retained in `input/` because the quality-control script must reproduce the 2,676 complete-day sample. The three USGS input files retain the exact 1995-10-01 through 2025-09-30 daily records used in the hydrological calculations.
