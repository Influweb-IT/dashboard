import os
import gettext

import numpy as np
import geopandas as gpd
import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
from scipy.stats import beta

locale_dir = os.path.join(os.path.dirname(__file__), 'locales')
domain = 'dashboard'
input_dir = os.environ.get('DASHBOARD_DATA_DIR', '/data/dashboard')
ready_sentinel = os.path.join(input_dir, '.READY')


def _ready_mtime() -> float:
    try:
        return os.path.getmtime(ready_sentinel)
    except FileNotFoundError:
        return 0.0


@st.cache_data
def _load_series(_ready_mtime: float):
    """Load indicator CSVs as series. Cache is keyed on the
    .READY sentinel mtime so it invalidates only after the aggregate cron
    publishes a new dataset."""
    return {
        "ILI_incidence": pd.read_csv(os.path.join(input_dir, 'ILI_incidence.csv'), index_col=0, header=0).squeeze(),
        "ARI_incidence": pd.read_csv(os.path.join(input_dir, 'ARI_incidence.csv'), index_col=0, header=0).squeeze(),
        "active_users":  pd.read_csv(os.path.join(input_dir, 'active_users.csv'),  index_col=0, header=0).squeeze(),
        "gender":        pd.read_csv(os.path.join(input_dir, 'gender.csv'),        index_col=0, header=0).squeeze(),
        "education":     pd.read_csv(os.path.join(input_dir, 'education.csv'),     index_col=0, header=0).squeeze(),
        "occupation":    pd.read_csv(os.path.join(input_dir, 'occupation.csv'),    index_col=0, header=0).squeeze(),
        "age":           pd.read_csv(os.path.join(input_dir, 'age.csv'),           index_col=0, header=0).squeeze(),
    }


@st.cache_data
def _load_reg_map(_ready_mtime: float):
    df = gpd.read_file(os.path.join(input_dir, 'reg_map.csv'), ignore_geometry=True)
    df['geometry'] = gpd.GeoSeries.from_wkt(df['geometry'])
    df['count'] = df['count'].astype(float)
    df['ar'] = df['ar'].astype(float)
    return gpd.GeoDataFrame(df)


def _incidence_plot(series):

    def clopper_pearson(p, n):
        alpha = 0.05
        k = p * n
        p_u, p_o = {}, {}
        ci_u, ci_o = {}, {}
        for season in p.keys():
            kk = k[season]
            nn = n[season]
            p_u[season], p_o[season] = beta.ppf([alpha/2, 1 - alpha/2], [kk, kk + 1], [nn - kk + 1, nn - kk])
            if np.isnan(p_u[season]):
                p_u[season] = 0
            if np.isnan(p_o[season]):
                p_o[season] = 1
            ci_u[season], ci_o[season] = p[season] - p_u[season], p_o[season] - p[season]
        d = pd.DataFrame.from_dict([ci_u, ci_o])
        return d

    rescaling = 1000

    incidence = series["ILI_incidence"]
    incidence_ARI = series["ARI_incidence"]
    wau = series["active_users"]

    st.title(_('ILI incidence'))
    st.write(_('In this section you can find updated data collected by Influweb regarding influenza symptoms.'),
             _("The graph below shows the incidence curve of probable cases of influenza-like illness (ILI) and cases of acute respiratory syndrome (ARI) observed throughout Italy in the last year. The solid line represents an estimate of the incidence in the current week, the transparent area represents the 95% uncertainty of the estimate."))

    ili_label = _('ILI')
    ari_label = _('ARI')

    tab1, tab2 = st.tabs([ili_label, ari_label])

    incidence_y_label = _('incidence (‰)')
    incidence_x_label = _('onset week')

    with tab1:
        fig1, ax1 = plt.subplots(figsize=(12, 4))
        pd.Series(incidence).plot(color='#118AB2', marker='o', ls='-', markersize=4, alpha=.8, ax=ax1, label=ili_label)
        ILI_down = pd.Series(incidence) - (clopper_pearson(pd.Series(incidence)/rescaling, wau)*rescaling).T[0]
        ILI_up = pd.Series(incidence) + (clopper_pearson(pd.Series(incidence)/rescaling, wau)*rescaling).T[1]
        ax1.fill_between(pd.Series(incidence).index, ILI_down, ILI_up, alpha=.3, color='#118AB2')
        plt.ylabel(incidence_y_label)
        plt.xlabel(incidence_x_label)
        ax1.spines[['right', 'top']].set_visible(False)
        st.pyplot(fig1)
    with tab2:
        fig2, ax2 = plt.subplots(figsize=(12, 4))
        pd.Series(incidence_ARI).plot(color='#073B4C', marker='o', ls='-', markersize=4, alpha=.8, ax=ax2, label=ari_label)
        ARI_down = pd.Series(incidence_ARI) - (clopper_pearson(pd.Series(incidence_ARI)/rescaling, wau)*rescaling).T[0]
        ARI_up = pd.Series(incidence_ARI) + (clopper_pearson(pd.Series(incidence_ARI)/rescaling, wau)*rescaling).T[1]
        ax2.fill_between(pd.Series(incidence_ARI).index, ARI_down, ARI_up, alpha=.3, color='#073B4C')
        plt.ylabel(incidence_y_label)
        plt.xlabel(incidence_x_label)
        ax2.spines[['right', 'top']].set_visible(False)
        st.pyplot(fig2)


def _demographic_composition_plot(series):

    gender = series["gender"]
    education = series["education"]
    occupation = series["occupation"]
    age = series["age"]

    gender = gender.rename({'Male': _('Male'), 'Female': _('Female'), 'Other': _('Other')})
    occupation = occupation.rename({'full_time': _('Full time'), 'retired': _('Retired'), 'self-employed': _('Self-employed'),
                                    'student': _('Student'), 'part_time': _('Part-time'), 'homemaker': _('Homemaker'), 'unemployed': _('Unemployed'),
                                    'other': _('Other'), 'on leave': _('On leave')})
    education = education.rename({'master_phd': _('Master or PhD'), 'high_school': _('High school'), 'bachelor': _('Bachelor'),
                                  'int_school': _('Intermediate school'), 'none': _('None'), 'student': _('Student')})
    age = age.reindex(['<18', '18-40', '41-65', '>65'])

    st.title(_('Demographic composition of participants'))

    st.write(_('In this section we show the demographic characteristics of the participants in the current season.'),
             _('The graphs below show the demographic composition in terms of gender, age, education, and occupation.'))

    fig3, ax3 = plt.subplots(figsize=(10, 7), nrows=2, ncols=2)

    gender.plot.bar(ax=ax3[0, 0], color='#621708', rot=0)
    ax3[0, 0].set_title(_('Gender'))
    ax3[0, 0].set_xlabel('')
    ax3[0, 0].spines[['right', 'top']].set_visible(False)
    age.plot.bar(ax=ax3[0, 1], color='#F6AA1C', rot=0)
    ax3[0, 1].set_title(_('Age'))
    ax3[0, 1].set_xlabel('')
    ax3[0, 1].spines[['right', 'top']].set_visible(False)
    education.plot.bar(ax=ax3[1, 0], color='#BC3908')
    ax3[1, 0].set_title(_('Education'))
    ax3[1, 0].set_xlabel('')
    ax3[1, 0].spines[['right', 'top']].set_visible(False)
    occupation.plot.bar(ax=ax3[1, 1], color='#941B0C')
    ax3[1, 1].set_title(_('Occupation'))
    ax3[1, 1].set_xlabel('')
    ax3[1, 1].spines[['right', 'top']].set_visible(False)

    fig3.text(0.0, 0.6, _('Number of participants in the 2023-2024 season'), va='center', rotation='vertical')

    plt.tight_layout()
    st.pyplot(fig3)


def _geo_plot(gdf):

    st.title(_('Geographic aspects'))

    st.write(_("The first map shows the cumulative incidence in the 2023-2024 season of probable cases of influenza-like illness (ILI) reported in each region by Influweb participants."),
             _('The second map shows the regional coverage of participants in each region expressed as the number of participants per 100,000 inhabitants.'))

    tab4, tab5 = st.tabs([_('ILI attack rate'), _('Participants')])

    with tab4:
        fig4, ax4 = plt.subplots(figsize=(6, 6))
        gdf.plot(ax=ax4, cmap='Blues', column='ar', legend=True, edgecolor="w", linewidth=.3,
                 legend_kwds={"label": _('Attack rate per 100,000 inhabitants in the 2023-2024 season'), "orientation": "vertical", "shrink": 0.6})
        ax4.axis('off')
        st.pyplot(fig4)

    with tab5:
        fig5, ax5 = plt.subplots(figsize=(6, 6))
        gdf.plot(ax=ax5, cmap='Reds', column='count', legend=True, edgecolor="w", linewidth=.3,
                 legend_kwds={"label": _('Participants per 100,000 inhabitants in the 2023-2024 season'), "orientation": "vertical", "shrink": 0.6})
        ax5.axis('off')
        st.pyplot(fig5)


def draw(language: str):
    translation = gettext.translation(domain, localedir=locale_dir, languages=[language])
    translation.install()

    mtime = _ready_mtime()
    series = _load_series(mtime)
    gdf = _load_reg_map(mtime)

    _incidence_plot(series)
    _demographic_composition_plot(series)
    _geo_plot(gdf)
