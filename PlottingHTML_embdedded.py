import os
import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import beta
import gettext
import json
from shapely.ops import orient
import plotly.graph_objects as go
import plotly.express as px


locale_dir = 'locales'
domain = 'dashboard'
input_dir = 'data/dashboard'
OUTPUT_HTML = "dashboard.html"


# -------------------------
# Utilities
# -------------------------
def clopper_pearson(p, n):
    alpha = 0.05
    k = p * n
    p_u, p_o = {}, {}
    for season in p.index:
        kk = k[season]
        nn = n[season]
        lo, hi = beta.ppf(
            [alpha / 2, 1 - alpha / 2],
            [kk, kk + 1],
            [nn - kk + 1, nn - kk]
        )
        p_u[season] = 0 if np.isnan(lo) else lo
        p_o[season] = 1 if np.isnan(hi) else hi
    return pd.DataFrame({"lower": p_u, "upper": p_o})


# -------------------------
# Incidence plots
# -------------------------
def incidence_fig(incidence, wau, label, color, ylabel, xlabel):
    rescaling = 1000
    p = incidence / rescaling
    ci = clopper_pearson(p, wau) * rescaling

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=incidence.index,
        y=incidence,
        name=label,
        line=dict(color=color)
    ))

    fig.add_trace(go.Scatter(
        x=incidence.index,
        y=incidence - ci["lower"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        name=_("95% CI")

    ))

    fig.add_trace(go.Scatter(
        x=incidence.index,
        y=incidence + ci["upper"],
        mode="lines",
        fill="tonexty",
        fillcolor=color.replace("1)", "0.3)"),
        line=dict(width=0),
        name=_("95% CI")
    ))

    fig.update_layout(
        height=350,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title=xlabel,
        yaxis_title=ylabel
    )

    return fig


# -------------------------
# Demographics
# -------------------------
def bar_fig(series, title, color):
    fig = px.bar(
        x=series.index,
        y=series.values,
        labels={"x": "", "y": ""},
        title=title
    )
    fig.update_traces(marker_color=color)
    fig.update_layout(height=300)
    return fig

# -------------------------
# Symptoms
# -------------------------

def bar_fig_symptoms(series, title, color, xaxis_label=""):
    # Round the values to 2 decimals
    rounded_values = series.round(2)

    # Translate symptom names
    translated_index = [_(symptom) for symptom in series.index]

    # Create a DataFrame for Plotly Express
    df = pd.DataFrame({
        "": translated_index,
        _("Prevalence %"): rounded_values
    })

    fig = px.bar(
        df,
        x = _("Prevalence %"),
        y = "",
        labels={"x": xaxis_label, "y": ""},
        title=title,
        orientation="h",
        hover_data=[_("Prevalence %")]
    )

    fig.update_traces(
        marker_color=color,
        hovertemplate="%{y}: %{customdata[0]:.2f}%<extra></extra>"
    )

    fig.update_layout(
        height=max(300, 25*len(series)),
        yaxis=dict(autorange="reversed")
    )

    return fig


# -------------------------
# Geography
# -------------------------


def prepare_geo(gdf, region_col="DEN_REG"):
    gdf = gdf.copy()
    gdf[region_col] = gdf[region_col].astype(str)
    geojson = json.loads(gdf.to_json())
    return gdf, geojson


def normalize_geometry(gdf, region_col):
    gdf = gdf.copy()

    # Fix invalid geometries
    gdf["geometry"] = gdf["geometry"].buffer(0)

    # Explode multipolygons
    gdf = gdf.explode(index_parts=False)

    # Re-dissolve by region
    gdf = gdf.dissolve(by=region_col, as_index=False)

    # Force consistent ring orientation
    gdf["geometry"] = gdf["geometry"].apply(lambda g: orient(g, sign=1.0))

    return gdf



def geo_fig(gdf, geojson, column, region_col, title, colorscale, legend):
    # Include color column in hover_data for robust hover
    fig = px.choropleth(
        gdf,
        geojson=geojson,
        locations=region_col,
        featureidkey=f"properties.{region_col}",
        color=column,
        color_continuous_scale=colorscale,
        labels={column: legend},        # ensures colorbar has legend
        hover_data={column: True},      # passes color to hovertemplate
        projection="mercator"
    )

    # Fit map bounds
    fig.update_geos(
        fitbounds="locations",
        visible=False
    )

    # Layout
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        height=500,
        paper_bgcolor="white",
        plot_bgcolor="white",
        dragmode="pan"  # allows panning with mouse drag
        # zoom is controlled only via buttons; scroll wheel does nothing
    )

    # Hovertemplate using customdata
    fig.update_traces(
        marker_line_width=1,
        marker_line_color="black",
        hovertemplate=f"<b>%{{location}}</b><br>{legend}: %{{customdata[0]}}<extra></extra>"
    )

    return fig




# -------------------------
# Main
# -------------------------
def draw(language: str):
    translation = gettext.translation(domain, localedir=locale_dir, languages=[language])
    translation.install()

    # ---- Load data
    incidence = pd.read_csv(f"{input_dir}/ILI_incidence.csv", index_col=0).squeeze()
    incidence_ari = pd.read_csv(f"{input_dir}/ARI_incidence.csv", index_col=0).squeeze()

    # Replace labels for gender
    incidence = incidence.rename({
        'onset_week': _('Onset week')
    })

    # Replace labels for gender
    incidence_ari = incidence_ari.rename({
        'onset_week': _('Onset week')
    })

    wau = pd.read_csv(f"{input_dir}/active_users.csv", index_col=0).squeeze()

    gender = pd.read_csv(f"{input_dir}/gender.csv", index_col=0).squeeze()
    age = pd.read_csv(f"{input_dir}/age.csv", index_col=0).squeeze()
    education = pd.read_csv(f"{input_dir}/education.csv", index_col=0).squeeze()
    occupation = pd.read_csv(f"{input_dir}/occupation.csv", index_col=0).squeeze()

    symptoms = pd.read_csv(f"{input_dir}/symptoms.csv", index_col=0).squeeze()


    # Replace labels for gender
    gender = gender.rename({
        'Male': _('Male'),
        'Female': _('Female'),
        'Other': _('Other')
    })

    # Replace labels for occupation
    occupation = occupation.rename({
        'full_time': _('Full time'),
        'retired': _('Retired'),
        'self-employed': _('Self-employed'),
        'student': _('Student'),
        'part_time': _('Part-time'),
        'homemaker': _('Homemaker'),
        'unemployed': _('Unemployed'),
        'other': _('Other'),
        'on leave': _('On leave')
    })

    # Replace labels for education
    education = education.rename({
        'master_phd': _('Master or PhD'),
        'high_school': _('High school'),
        'bachelor': _('Bachelor'),
        'int_school': _('Intermediate school'),
        'none': _('None'),
        'student': _('Student')
    })

    symptoms = symptoms.rename({
        'fever': _('Fever'),
        'chills': _('Chills'),
        'runny_blocked_nose': _('Runny or blocked nose'),
        'sneezing': _('Sneezing'),
        'sore_throat': _('Sore throat'),
        'cough': _('Cough'),
        'shortness_breath': _('Shortness of breath'),
        'headache': _('Headache'),
        'muscle_joint_pain': _('Muscle/joint pain'),
        'chest_pain': _('Chest pain'),
        'malaise': _('Malaise'),
        'loss_appetite': _('Loss of appetite'),
        'coloured_sputum': _('Coloured sputum'),
        'watery_bloodshot_eyes': _('Watery, bloodshot eyes'),
        'nausea': _('Nausea'),
        'vomiting': _('Vomiting'),
        'diarrhoea': _('Diarrhoea'),
        'stomach_ache': _('Stomach ache'),
        'rash': _('Rash'),
        'loss_taste': _('Loss of taste'),
        'nose_bleed': _('Nose bleed'),
        'loss_smell': _('Loss of smell'),
        'sudden_onset': _('Sudden onset'),
        'sudden_fever': _('Sudden fever'),
        'other': _('Other')
        }
    )


    # For age, reorder or rename if needed
    age = age.reindex(['<18','18-40','41-65','>65'])


    df = pd.read_csv(os.path.join(input_dir, "reg_map.csv"))
    # Create geometry
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.GeoSeries.from_wkt(df["geometry"])
    )

    gdf = gdf.set_crs(epsg=32632)   # UTM zone 32N (most common)
    # gdf = gdf.set_crs(epsg=3003)  # Monte Mario / Italy
    # gdf = gdf.set_crs(epsg=25832) # ETRS89 / UTM 32N

    # ✅ REPROJECT TO LAT/LON
    gdf = gdf.to_crs(epsg=4326)

    gdf = gdf[["DEN_REG", "ar", "count", "geometry"]]
    gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.01, preserve_topology=True)

    gdf["DEN_REG"] = gdf["DEN_REG"].astype(str).str.strip()

    # Build GeoJSON AFTER reprojection
    geojson = json.loads(gdf.to_json())


    # ---- Build figures
    ili_fig = incidence_fig(
        incidence, wau, _("ILI"), "rgba(17,138,178,1)",
        _("incidence (‰)"), _("onset week")
    )

    ari_fig = incidence_fig(
        incidence_ari, wau, _("ARI"), "rgba(7,59,76,1)",
        _("incidence (‰)"), _("onset week")
    )

    demo_figs = [
        bar_fig(gender, _("Gender"), "#621708"),
        bar_fig(age, _("Age"), "#F6AA1C"),
        bar_fig(education, _("Education"), "#BC3908"),
        bar_fig(occupation, _("Occupation"), "#941B0C"),
    ]

    geo_ili = geo_fig(
        gdf,
        geojson,
        column="ar",
        region_col="DEN_REG",
        title=_("ILI attack rate"),
        colorscale="Blues",
        legend=_("Attack rate per 100,000 inhabitants")
    )

    geo_part = geo_fig(
        gdf,
        geojson,
        column="count",
        region_col="DEN_REG",
        title=_("Participants"),
        colorscale="Reds",
        legend=_("Participants per 100,000 inhabitants")
    )


    symptoms_fig = bar_fig_symptoms(
        symptoms,
        _("Symptoms"),
        "#A44A3F",
        xaxis_label=_("Prevalence (%)")
    )


    #remove unnecessary text from the hovering text
    for fig in [geo_ili, geo_part]:
    # Update hovertemplate
        fig.update_traces(
            hovertemplate="<b>%{location}</b><br>%{z:.2f}<extra></extra>"
        )
        # Update each trace's colorbar
        for trace in fig.data:
            if hasattr(trace, "colorbar") and trace.colorbar is not None:
                trace.colorbar.title.side = "right"  # vertical title
                trace.colorbar.title.font = dict(size=12)
                trace.colorbar.tickfont = dict(size=10)
                trace.colorbar.thickness = 15
                trace.colorbar.len = 0.8



    # Update the colorbar layout for vertical label

    # Update the colorbar layout for vertical label
    geo_ili.update_layout(
        coloraxis_colorbar=dict(
            title=_("ILI attack rate per 100,000 inhabitants"),
            title_side="right",   # put title on the right of the colorbar
            title_font=dict(size=12),
            tickfont=dict(size=10),
            thickness=15,
            len=0.8
        )
    )
    geo_part.update_layout(
        coloraxis_colorbar=dict(
            title=_("Participants per 100,000 inhabitants"),
            title_side="right",   # put title on the right of the colorbar
            title_font=dict(size=12),
            tickfont=dict(size=10),
            thickness=15,
            len=0.8
        )
    )

    # Update the colorbar layout for vertical label
    geo_part.update_layout(

    )

    for fig in demo_figs + [symptoms_fig]:
        fig.update_traces(
            hovertemplate="%{x}: %{y}<extra></extra>"
            )

    # ---- Assemble HTML (Plotly.js embedded once)

    Title_incidence = _('Syndromic incidence')
    Title_demo = _('Demographic composition')
    Title_geo = _('Geographic aspects')
    Title_symp = _('Symptoms of the week')
    Text_incidence = _("The graph below shows the incidence curve of probable cases of influenza-like illness (ILI) and acute respiratory syndrome (ARI) observed throughout Italy in the current season. The solid line represents an estimate of the incidence in the current week, the shaded area represents the 95% confidence internval of the estimate.")
    Text_demo = _("In this section we show the demographic composition in terms of gender, age, education, and occupation of participants in the current season")
    Text_map1 = _("The first map shows the cumulative incidence in the current season of influenza-like illness (ILI) reported by participants in each region by")
    Text_map2 = _("The second map shows the regional coverage of participants in each region expressed as the number of participants per 100,000 inhabitants.")
    Text_symp = _("The following chart shows the prevalence of specific symptoms among participants reporting any symptoms")

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Influweb Dashboard</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: sans-serif; margin: 40px; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            .map-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px; }}
        </style>
    </head>
    <body>

    <h1>{Title_incidence}</h1>
    <p style="font-size:14px; "> {Text_incidence} </p>
    {ili_fig.to_html(full_html=False, include_plotlyjs="cdn")}
    {ari_fig.to_html(full_html=False, include_plotlyjs=False)}

    <h1>{Title_demo}</h1>
    <p style="font-size:14px; "> {Text_demo}</p>
    <div class="grid">
        {''.join(fig.to_html(full_html=False, include_plotlyjs=False) for fig in demo_figs)}
    </div>

    <h1>{Title_geo}</h1>
    <p style="font-size:14px; "> {Text_map1}</p>
    <p style="font-size:14px; "> {Text_map2}</p>
    <div class="map-grid">
        {geo_ili.to_html(full_html=False, include_plotlyjs=False)}
        {geo_part.to_html(full_html=False, include_plotlyjs=False)}
    </div>

    <h1>{Title_symp}</h1>
    <p style="font-size:14px; "> {Text_symp}</p>

    <div class="grid">
        {symptoms_fig.to_html(full_html=False, include_plotlyjs=False)}
    </div>


    </body>
    </html>
    """


    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    draw("it")
