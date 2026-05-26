## Requirements

```sh
conda env create -f environment.yml
conda activate <env-name>
```

## Generate Dashboard data

`DataTreatment.py` reads raw exports from a versioned directory and writes processed CSVs.

**Expected input layout:**

```
data/raw/
└── <YYYY-Www>/          # e.g. 2026-W22 — most recent week wins
    ├── intake.csv
    ├── weekly.csv
    └── .READY           # sentinel; must exist or the directory is skipped
```

The raw data should contain all data you want to analyze, not just the one-week data belonging to the name of the directory.
The directory are named weekly because in production we want to keep track of the export performed each week, but each export is a full-season export.

Prepare the raw CSVs and run:

```sh
RAW_DIR=data/raw DASHBOARD_DATA_DIR=data/dashboard python DataTreatment.py
```

You can override the week with `RAW_WEEK=2026-W22` in case you have multiple weeks and want to run the analysis on a specific set of data

The script generates:
- active users.csv
- age.csv
- ARI_incidence.csv
- ILI_incidence.csv
- education.csv
- gender.csv
- occupation.csv
- reg_map.csv (geodataframe)

## Run the Dashboard

`./run.sh`

This generates:
- two tabs with ILI and ARI incidence for a given season
- histograms of participants composition by age, gender, education and occupation
- two maps for ILI cumulative incidence and n of participants per region in a given season

## Internationalization

Internationalization is handled by `gettext`

When changing `Plotting.py` source code by adding new strings to be translated, run 

`xgettext --no-location -o locales/dashboard.pot Plotting.py`

After doing this you need to merge the newly generate .pot file with the existing translations

`msgmerge -U locales/<language_code>/LC_MESSAGES/dashboard.po locales/dashboard.pot`
