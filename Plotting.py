import time
import streamlit as st

import _data


def draw(language: str):
    t0 = time.time()
    print(f"[draw] start (lang={language})", flush=True)

    
    st.set_page_config(layout="wide", page_title="Influweb Dashboard")

    st.html('<script src="https://cdn.jsdelivr.net/npm/@iframe-resizer/child@5/index.umd.js"></script>')
    st.markdown("""<style>
#MainMenu, footer, header { visibility: hidden; }
</style>""", unsafe_allow_html=True)

    _ = _data._t(language)
    mtime = _data.ready_mtime()
    fig1, fig2, fig3, fig4, fig5 = _data.load_figures(mtime, language)
    print(f"[draw] figures ready in {time.time()-t0:.2f}s", flush=True)

    st.title(_("ILI incidence"))
    st.write(
        _("In this section you can find updated data collected by Influweb regarding influenza symptoms."),
        _("The graph below shows the incidence curve of probable cases of influenza-like illness (ILI) and cases of acute respiratory syndrome (ARI) observed throughout Italy in the last year. The solid line represents an estimate of the incidence in the current week, the transparent area represents the 95% uncertainty of the estimate."),
    )
    tab1, tab2 = st.tabs([_("ILI"), _("ARI")])
    with tab1:
        st.image(fig1, use_column_width=True)
    with tab2:
        st.image(fig2, use_column_width=True)

    st.title(_("Demographic composition of participants"))
    st.write(
        _("In this section we show the demographic characteristics of the participants in the current season."),
        _("The graphs below show the demographic composition in terms of gender, age, education, and occupation."),
    )
    st.image(fig3, use_column_width=True)

    st.title(_("Geographic aspects"))
    st.write(
        _("The first map shows the cumulative incidence in the 2023-2024 season of probable cases of influenza-like illness (ILI) reported in each region by Influweb participants."),
        _("The second map shows the regional coverage of participants in each region expressed as the number of participants per 100,000 inhabitants."),
    )
    tab4, tab5 = st.tabs([_("ILI attack rate"), _("Participants")])
    with tab4:
        st.image(fig4, use_column_width=True)
    with tab5:
        st.image(fig5, use_column_width=True)

    print(f"[draw] complete in {time.time()-t0:.2f}s", flush=True)

if __name__ == "__main__":
    lang = st.query_params.get("lang", "it")
    draw(lang)
