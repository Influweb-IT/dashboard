
**Requirements**

see req folder for list of packages of the streamlit conda environment
#### note: the scripts should run in the same folder of the streamlit environment

anaconda
python 3.9 (conda)  
streamlit (pip)  
pandas (conda)  
numpy (conda)  
scipy (conda)  
geopandas (conda)  
pyogrio (pip)  


path of data: "/Users/mattiamazzoli/influweb-resources/syndromes/" (this can be changed to a directory in Igea where we update data automatically every week)

**Code flow**

1) streamlit run DataTreatment.py

Input files:
- pop_reg.csv (regions populations)
- Limiti01012024_g-2 (regions shapefile)
- "./intake/" (intake files obtained with bulk extraction)
- "./weekly/" (weekly files obtained with bulk extraction)

This generates:
- active users.csv
- age.csv
- ARI_incidence.csv
- ILI_incidence.csv
- education.csv
- gender.csv
- occupation.csv
- reg_map.csv (geodataframe)

2) streamlit run Plotting.py

Input files:
- active users.csv
- age.csv
- ARI_incidence.csv
- ILI_incidence.csv
- education.csv
- gender.csv
- occupation.csv
- reg_map.csv (geodataframe)

This generates:
- two tabs with ILI and ARI incidence for a given season
- histograms of participants composition by age, gender, education and occupation
- two maps for ILI cumulative incidence and n of participants per region in a given season
