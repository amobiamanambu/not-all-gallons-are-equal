# Not All Gallons Are Equal: analysis reproducibility package

This repository package reproduces the numerical analyses and manuscript tables for *Not All Gallons Are Equal: A Hydrological Framework for Interpreting Data Center Water Use*. Its data scope is limited to records used in the manuscript. Primary evidence is cited directly in the manuscript tables, figure captions, and reference list; this archive supplies the corresponding machine-readable data, provenance, and verification code.

## What is included

- `data/input/`: frozen machine-readable inputs used by the analysis. These include 97 named Google location-years used in the U.S. and FY2025 global panels, four aggregate Google rows retained only for the documented quality-control check, 70 U.S. Meta facility-years, four matched U.S. AWS regions, the 26-location U.S. Aqueduct screen, three complete USGS daily-flow series, the City of Mesa source extract, four Quincy evidence records, and the archived 72-row cooling-model output.
- `data/analysis_ready/`: source-linked tables produced by the first analysis step. Reported values carry a stable `source_id`, a public URL, and an exact page, station, table, dataset, or section locator where available.
- `analysis/`: four sequential scripts that prepare the data, reproduce the statistics, build manuscript tables and metadata, and perform three-level QA/QC.
- `figures/`: one self-contained folder for each manuscript Figure 3-9. Each folder contains the final plotting script and its exact source-linked plotting CSV file(s); running a script writes SVG and 600-dpi JPG files to that folder's `output/` directory.
- `results/`: machine-readable headline results and one CSV for each manuscript table.
- `metadata/source_register.csv`: the authoritative mapping from every stable source identifier to bibliographic information, URL, source locator, verification status, and scientific boundary.
- `metadata/dataset_catalog.csv`: file-level inventory with dimensions and SHA-256 checksums.
- `metadata/variable_dictionary.csv`: column-level definitions and units.
- `metadata/manuscript_value_source_map.csv`: row-level crosswalk from every row of Tables 1-6 to its source IDs, exact locators, reported/derived status, and analysis script.
- `metadata/figure_source_map.csv`: figure-level crosswalk from Figures 1-9 to the primary sources, locators, and scientific boundaries stated in their captions.
- `metadata/manuscript_data_map.csv`: compact inventory linking Figures 3-9 and Tables 1-6 to the released files and record subsets that generate them.
- `metadata/known_source_issues.csv`: the two explicitly documented source-version issues; neither is silently repaired.
- `data/model_archive/`: the original thermodynamic notebook, Python functions, COP objects, and TMY3 files retained for an optional full cooling-model rebuild.
- `Data_and_Sources.xlsx`: plain, non-colored human-readable workbook containing the source register, figure and table provenance maps, dataset catalog, data dictionary, manuscript-scope analysis-ready data, and manuscript tables. The complete 65,748-row derived pressure table remains in CSV and is indexed by checksum in the workbook to keep the human-readable file usable.

## Reproduce the analysis

Python 3.10 or newer is required. The verified dependency versions are listed in `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_all.py
```

The final command must end with a `PASS` message. The machine-readable QA report is `qa/three_level_qaqc.csv` and its summary is `qa/three_level_qaqc_summary.json`.

To reproduce an individual figure, enter its folder and run the colocated script. For example, `cd figures/Figure_06 && python figure_06.py`. Extra provenance columns in the CSV files are ignored by the plotting code but preserve the stable source IDs, exact locators, and scientific boundary for every plotted record.

To reproduce the analysis and all figures non-interactively, run `python run_all.py --figures`. This writes SVG and 600-dpi JPG outputs beneath each figure folder.

Files named `table_*` in `results/` retain analytical precision. Files named `manuscript_table_*` are publication-display copies rounded exactly as shown in the Word manuscript; they are not separate analyses.

## Evidence streams and denominators

The workflow does not pool quantities with incompatible denominators:

1. Google location water values are annual withdrawal, discharge, and operator-estimated consumption.
2. Meta facility intensity divides water withdrawal by total-facility electricity and is explicitly **not** called WUE.
3. AWS PUE and WUE use the operator's IT-energy denominator and are compared only for matched regions and years.
4. Source-relative pressure is a standardized 250 MW screen using a documented source component, an archived cooling scenario, and observed daily flow. It is not facility impact, available water, legal allocation, or sustainable capacity.
5. Mesa and Quincy are managed-system cases. Municipal pathways and differently defined reuse quantities are not assigned to individual facilities or summed into false mass balances.

## Known source issues

- Google's FY2024 aggregate `Other data center locations` row prints withdrawal of 828.9 MG, discharge of 60.0 MG, and consumption of 786.9 MG. Withdrawal minus discharge equals 768.9 MG. The package preserves the printed value, flags the inconsistency, and excludes that aggregate row from named-location consumption results.
- AWS FY2025 regional values are tied to the official webpage archived on 2026-09-05. The retrieval date and SHA-256 are preserved so later webpage changes cannot silently alter the results.

## Data licensing and primary reports

Large provider reports and the 261 MB Aqueduct distribution are not duplicated in this GitHub-ready folder. Their official URLs, exact report pages or dataset versions, and archived-file hashes are recorded in `metadata/source_register.csv`. The 26-location Aqueduct extract used in Figure 3 is included. Users requiring the full original distributions should obtain them from the cited publishers and observe their terms.

## Scope decisions

The release excludes broader working collections that do not generate a manuscript result. It therefore omits non-U.S. historical Google rows, non-U.S. Meta facility-years, unmatched AWS regions, the redundant operator pass-through panel, and the unused Saint-Ghislain regulatory source-tracing records. The St. Ghislain FY2025 accounting observation remains in the 40-location Google comparison because Figure 9 uses it and cites Google (2026), p. 97. The 32,874 USGS rows are retained because Figures 6 and 8 and Table 4 use the three 10,958-day station records directly.

## Archived cooling-model rebuild

The standard workflow uses `data/input/monthly_cooling_water_intensity.csv`, whose 72 rows were previously regenerated from 52,560 hourly evaluations and frozen after QA. To inspect or rerun the full model, use `data/model_archive/Thermodynamic.ipynb` with `requirements_optional_cooling_model.txt`. The manuscript's `central` case is a named archived parameter vector, not an arithmetic midpoint.
