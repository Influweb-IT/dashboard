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



