
from matplotlib import *
import numpy as np
import geopandas as gpd
import streamlit as st

#pandas and matplotlib

import pandas as pd
import csv
from matplotlib import pyplot as plt

#data management
import os

# ## Get Data

from scipy.stats import beta
def clopper_pearson(p,n):
    alpha = 0.05
    k = p*n
    p_u,p_o={},{}
    ci_u,ci_o={},{}
    for season in p.keys():
        kk=k[season]
        nn=n[season]
        p_u[season], p_o[season] = beta.ppf([alpha/2, 1 - alpha/2], [kk, kk + 1], [nn - kk + 1, nn - kk])
        if np.isnan(p_u[season]):
            p_u[season] = 0
        if np.isnan(p_o[season]):
            p_o[season] = 1
        ci_u[season], ci_o[season] = p[season] - p_u[season], p_o[season] - p[season] #translate ci to interval from the estimation
    d = pd.DataFrame.from_dict([ci_u, ci_o])
    return d

rescaling = 1000

input_dir = 'data/dashboard'

# get epi values
incidence = pd.read_csv(os.path.join(input_dir, 'ILI_incidence.csv'), index_col=0, header=0).squeeze()
incidence_ARI = pd.read_csv(os.path.join(input_dir, 'ARI_incidence.csv'), index_col=0, header=0).squeeze()
wau = pd.read_csv(os.path.join(input_dir, 'active_users.csv'), index_col=0, header=0).squeeze()



# get participants values

gender =  pd.read_csv(os.path.join(input_dir, 'gender.csv'), index_col=0, header=0).squeeze()
education =  pd.read_csv(os.path.join(input_dir, 'education.csv'), index_col=0, header=0).squeeze()
occupation =  pd.read_csv(os.path.join(input_dir, 'occupation.csv'), index_col=0, header=0).squeeze()
age =  pd.read_csv(os.path.join(input_dir, 'age.csv'), index_col=0, header=0).squeeze()

gender = gender.rename({'Male':'Maschio','Female':'Femmina','Other':'Altro'})
occupation = occupation.rename({'full_time':'Tempo pieno','retired':'In pensione','self-employed':'Autonomo',
                 'student':'Studente','part_time':'Part time','homemaker':'Domestico','unemployed':'Disoccupato',
                               'other':'Altro', 'on leave':'In congedo'})
education = education.rename({'master_phd':'Master o PhD','high_school':'Scuola superiore','bachelor':'Laurea triennale',
                 'int_school':'Scuola media','none':'Nessun titolo','student':'Sta ancora studiando'})
age= age.reindex(['<18','18-40','41-65','>65'])


st.title("Incidenza da sindromi simil-influenzali")


st.write("In questa sezione potete trovare i dati aggiornati raccolti da Influweb per quanto riguarda i sintomi influenzali.")

st.write("Il grafico riportato qui sotto mostra la curva di incidenza dei probabili casi di sindrome simil-influenzale (ILI) e casi di sindrome respiratoria acuta (ARI) osservati in tutta Italia nell'ultimo anno. La curva continua rappresenta una stima dell'incidenza nella settimana corrente, l'area trasparente rappresenta l'incertezza del 95% sulla stima.")


# Initialise variable
#https://coolors.co/palette/ef476f-ffd166-06d6a0-118ab2-073b4c

tab1, tab2 = st.tabs(["ILI", "ARI"])

with tab1:
    fig1,ax1=plt.subplots(figsize=(12,4))
    pd.Series(incidence).plot(color='#118AB2', marker='o', ls='-', markersize=4, alpha=.8, ax=ax1, label='ILI')
    ILI_down = pd.Series(incidence)-(clopper_pearson(pd.Series(incidence)/rescaling,wau)*rescaling).T[0]
    ILI_up = pd.Series(incidence)+(clopper_pearson(pd.Series(incidence)/rescaling,wau)*rescaling).T[1]
    ax1.fill_between(pd.Series(incidence).index, ILI_down, ILI_up, alpha=.3, color='#118AB2')
    plt.ylabel('incidence (‰)')
    plt.xlabel('onset week')
    ax1.spines[['right', 'top']].set_visible(False)
    st.pyplot(fig1)
with tab2:
    fig2,ax2=plt.subplots(figsize=(12,4))
    pd.Series(incidence_ARI).plot(color='#073B4C', marker='o', ls='-', markersize=4, alpha=.8, ax=ax2, label='ARI')
    ARI_down =  pd.Series(incidence_ARI)-(clopper_pearson(pd.Series(incidence_ARI)/rescaling,wau)*rescaling).T[0]
    ARI_up = pd.Series(incidence_ARI)+(clopper_pearson(pd.Series(incidence_ARI)/rescaling,wau)*rescaling).T[1]
    ax2.fill_between(pd.Series(incidence_ARI).index, ARI_down, ARI_up, alpha=.3, color='#073B4C')
    plt.ylabel('incidence (‰)')
    plt.xlabel('onset week')
    ax2.spines[['right', 'top']].set_visible(False)
    st.pyplot(fig2)



st.title("Composizione demografica dei partecipanti")

st.write("In questa sezione mostriamo le caratteristiche demografiche dei partecipanti nella stagione corrente.")
st.write("I grafici riportati qui sotto mostrano la composizione demograficha in termini di genere, età, educazione e occupazione.")


#https://coolors.co/palette/220901-621708-941b0c-bc3908-f6aa1c
fig3,ax3=plt.subplots(figsize=(10,7),nrows=2,ncols=2)

gender.plot.bar(ax=ax3[0,0],color='#621708',rot=0)
ax3[0,0].set_title('Genere')
ax3[0,0].set_xlabel('')
ax3[0,0].spines[['right', 'top']].set_visible(False)
age.plot.bar(ax=ax3[0,1],color='#F6AA1C',rot=0)
ax3[0,1].set_title('Età')
ax3[0,1].set_xlabel('')
ax3[0,1].spines[['right', 'top']].set_visible(False)
education.plot.bar(ax=ax3[1,0],color='#BC3908')
ax3[1,0].set_title('Educazione')
ax3[1,0].set_xlabel('')
ax3[1,0].spines[['right', 'top']].set_visible(False)
occupation.plot.bar(ax=ax3[1,1],color='#941B0C')
ax3[1,1].set_title('Occupazione')
ax3[1,1].set_xlabel('')
ax3[1,1].spines[['right', 'top']].set_visible(False)


fig3.text(0.0, 0.6, 'Numero participanti stagione 2023-2024', va='center', rotation='vertical')

plt.tight_layout()
st.pyplot(fig3)



st.title("Aspetti geografici")
st.write("La prima mappa mostra l'incidenza cumulativa nella stagione 2023-2024 dei probabili casi di sindrome simil-influenzale (ILI) riportati in ogni regione dai partecipanti di InfluWeb.")

st.write("La seconda mappa mostra la copertura regionale dei partecipanti in ogni regione espressa come numero di partecipanti per 100,000 abitanti.") 




df = gpd.read_file(os.path.join(input_dir, 'reg_map.csv'), ignore_geometry=True)
# Create geometry objects from WKT strings
df['geometry'] = gpd.GeoSeries.from_wkt(df['geometry'])
df['count'] = df['count'].astype(float)
df['ar'] = df['ar'].astype(float)

# Convert to GDF
gdf = gpd.GeoDataFrame(df)




tab4, tab5 = st.tabs(["ILI attack rate", "Partecipanti"])

with tab4:
    fig4, ax4 = plt.subplots(figsize=(6,6))
    gdf.plot(ax=ax4, cmap='Blues', column='ar', legend=True, edgecolor="w", linewidth=.3,
                 legend_kwds={"label": "Attack rate per 100 abitanti stagione 2023-2024", "orientation": "vertical","shrink":0.6})
    ax4.axis('off')
    st.pyplot(fig4)

with tab5:
    fig5, ax5 = plt.subplots(figsize=(6,6))
    gdf.plot(ax=ax5, cmap='Reds', column='count', legend=True, edgecolor="w", linewidth=.3,
                 legend_kwds={"label": "Partecipanti per 100,000 abitanti 1stagione 2023-2024", "orientation": "vertical","shrink":0.6})
    ax5.axis('off')
    st.pyplot(fig5)






