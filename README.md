## Requirements

Install the environment

`conda env create -f environment.yml`

and activate it.

## Generate Dashboard data

`python DataTreatment.py`

This script assumes you exported intakes and weeklies under `data/raw`

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

`streamlit run Plotting.py`

This generates:
- two tabs with ILI and ARI incidence for a given season
- histograms of participants composition by age, gender, education and occupation
- two maps for ILI cumulative incidence and n of participants per region in a given season
