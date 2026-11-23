"""Jamaica Brain Drain Tracker

Who leaves Jamaica for the United States, Canada and the United Kingdom, by what
route, and what their schooling cost the country, set against the remittances
the diaspora sends home.

Run locally:  streamlit run app.py
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"

BLUE = "#2a78d6"
ORANGE = "#e07b39"
GREEN = "#2a9d6b"
GREY = "#898781"
INK = "#0b0b0b"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

st.set_page_config(page_title="Jamaica Brain Drain Tracker", page_icon="✈️", layout="wide")


@st.cache_data
def load():
    panel = pd.read_csv(OUT / "panel.csv", index_col="year")
    summary = json.loads((OUT / "summary.json").read_text())
    return panel, summary


def style(fig, height=330, ytitle=None):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color=INK, size=13),
        hovermode="x unified", legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS, dtick=1)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=ytitle, rangemode="tozero")
    return fig


panel, S = load()
cost = S["education_cost"]

st.title("Jamaica Brain Drain Tracker")
st.caption(
    "Who leaves Jamaica for the United States, Canada and the United Kingdom, by what route, "
    "and what their schooling cost the country. Data: US Department of Homeland Security, "
    "Immigration, Refugees and Citizenship Canada, UK Home Office, World Bank, Bank of Jamaica."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("US green cards, FY2024", f"{S['us_2024']:,}", help="People born in Jamaica who became US permanent residents.")
c2.metric("Canada permanent residents, 2025", f"{S['canada_2025']:,}",
          f"{100 * (S['canada_2025'] / S['canada_peak'] - 1):.0f}% vs {S['canada_peak_year']} peak", delta_color="off")
c3.metric("Moved to US or Canada, 2024", f"{S['movers_per_1000_people_2024']} per 1,000",
          help="US green cards (FY2024) plus Canada permanent residents (2024), per 1,000 people in Jamaica.")
c4.metric("UK care and health visas, 2025", f"{S['uk_health_care_main']['2025']}",
          help=f"Main applicants. The peak was {S['uk_health_care_peak']} in {S['uk_health_care_peak_year']}.")

st.divider()

# 1. Flows by destination
st.subheader("How many leave, and where they go")
st.write(
    "Each chart has its own scale. The United States takes far more Jamaicans than Canada "
    "and the UK combined. US green cards in fiscal year 2024 were the highest in this series, which starts in 2014. Canada peaked in 2023 "
    "and fell after it cut its immigration targets."
)
cols = st.columns(3)
series = [
    ("United States", "us_green_cards", BLUE, "Green cards, people born in Jamaica (fiscal year)"),
    ("Canada", "canada_permanent_residents", GREEN, "Permanent residents, Jamaican citizens"),
    ("United Kingdom", "uk_long_stay_visas", ORANGE, "Visas other than visitor visas, Jamaican nationals"),
]
for col, (name, key, color, note) in zip(cols, series):
    s = panel[key].dropna()
    s = s[s.index <= 2025]
    fig = go.Figure(go.Scatter(x=s.index, y=s.values, mode="lines+markers", line=dict(color=color, width=2),
                               marker=dict(size=8), name=name, hovertemplate="%{y:,.0f}<extra></extra>"))
    col.markdown(f"**{name}**")
    col.plotly_chart(style(fig, 280), width='stretch')
    col.caption(note)

st.divider()

# 2. Routes
st.subheader("Most leave to join family, not for a job")
st.write(
    f"From 2015 to 2024, only {S['us_work_share_2015_2024_pct']}% of US green cards for "
    f"Jamaicans came through a job. In Canada the work share is higher, at "
    f"{S['canada_work_share_2015_2024_pct']}%, through programs like the Provincial Nominee Program. "
    "Family routes still bring skilled people, but the data do not record their jobs."
)
r1, r2 = st.columns(2)
yrs = panel.loc[2014:2024].index
fig = go.Figure()
fig.add_bar(x=yrs, y=panel.loc[yrs, "us_family_based"], name="Family", marker_color=BLUE)
fig.add_bar(x=yrs, y=panel.loc[yrs, "us_employment_based"], name="Job", marker_color=ORANGE)
fig.update_layout(barmode="group", bargap=0.25)
r1.markdown("**United States green cards by route**")
r1.plotly_chart(style(fig), width='stretch')
yrs = panel.loc[2015:2025].index
fig = go.Figure()
fig.add_bar(x=yrs, y=panel.loc[yrs, "canada_family"], name="Family", marker_color=BLUE)
fig.add_bar(x=yrs, y=panel.loc[yrs, "canada_economic"], name="Economic (work)", marker_color=ORANGE)
fig.update_layout(barmode="group", bargap=0.25)
r2.markdown("**Canada permanent residents by route**")
r2.plotly_chart(style(fig), width='stretch')

st.divider()

# 3. UK health and care
st.subheader("The UK care worker wave, and how it ended")
st.write(
    "When the UK opened its Health and Care Worker visa, Jamaican carers and nurses took it up fast. "
    "Grants to Jamaican main applicants rose from 5 in 2020 to 693 in 2023. The UK stopped new care "
    "workers bringing dependants in March 2024 and closed overseas recruitment of care workers on "
    "22 July 2025. Grants fell to 20 in 2025."
)
hc = panel.loc[2020:2025, "uk_health_care_main"]
sw = panel.loc[2020:2025, "uk_skilled_worker_main"]
fig = go.Figure()
fig.add_bar(x=hc.index, y=hc.values, name="Health and Care Worker", marker_color=ORANGE,
            text=[f"{v:,.0f}" for v in hc.values], textposition="outside")
fig.add_bar(x=sw.index, y=sw.values, name="Other Skilled Worker", marker_color=GREY)
fig.update_layout(barmode="group", bargap=0.25)
fig.add_annotation(x=2024, y=hc.max() * 1.05, text="Dependants banned<br>Mar 2024", showarrow=False,
                   font=dict(size=12, color=GREY))
fig.add_annotation(x=2025, y=hc.max() * 0.6, text="Overseas route closed<br>Jul 2025", showarrow=False,
                   font=dict(size=12, color=GREY))
st.plotly_chart(style(fig, 360, "Visas granted, main applicants"), width='stretch')
st.caption("UK Home Office entry clearance visas granted to Jamaican nationals. Dependants not shown.")

st.divider()

# 4. Cost calculator
st.subheader("What their schooling cost, against what comes back")
st.write(
    "A rough estimate of the public money Jamaica spent educating one year's movers to the US and "
    "Canada. Change the assumptions to see how much it matters. This is an illustration, "
    "not a full cost benefit study."
)
a, b = st.columns([1, 1.2])
with a:
    year = st.selectbox("Year of moving", [2024, 2023, 2022, 2021, 2019, 2018], index=0)
    movers = int(panel.loc[year, "us_green_cards"] + panel.loc[year, "canada_permanent_residents"])
    adult = st.slider("Share who finished school in Jamaica (%)", 30, 100, 70, 5,
                      help="Children and people who did not complete school are not counted.")
    grad = st.slider("Of those, share with a Jamaican degree (%)", 0, 60, 20, 5)
    st.caption(
        f"Public spending per student per year, from the World Bank, times GDP per person in "
        f"{cost['gdp_year']} (US${cost['gdp_per_person']:,.0f}): primary "
        f"US${cost['per_year']['primary']:,.0f} ({cost['share_primary_year']} share), secondary "
        f"US${cost['per_year']['secondary']:,.0f} ({cost['share_secondary_year']}), tertiary "
        f"US${cost['per_year']['tertiary']:,.0f} ({cost['share_tertiary_year']}). Six years of "
        "primary, five of secondary, four of university."
    )
schooled = movers * adult / 100
grads = schooled * grad / 100
total = (schooled - grads) * cost["school_leaver"] + grads * cost["graduate"]
remit = panel.loc[year, "remit_total_usd_m"] * 1e6
with b:
    st.metric(f"Moved to US or Canada in {year}", f"{movers:,}")
    st.metric("Public schooling they took with them", f"US${total / 1e6:,.0f}m")
    st.metric(f"Remittances received in {year}", f"US${remit / 1e6:,.0f}m",
              help="Bank of Jamaica gross remittance inflows. These come from the whole diaspora, "
                   "built up over decades, not just from that year's movers.")
    st.write(
        f"One year's movers carry about **{total / remit:.0%}** of one year's remittances in public "
        "schooling. Remittances come from the whole diaspora, built over decades, so this compares "
        "a one year loss with a yearly return on a much larger stock."
    )

st.divider()
with st.expander("About the data"):
    st.markdown(
        "- **United States:** DHS Yearbook of Immigration Statistics, Table 10, persons obtaining "
        "lawful permanent resident status by broad class of admission and country of birth, fiscal "
        "years 2014 to 2024. 'Family' is immediate relatives of US citizens plus family sponsored "
        "preferences.\n"
        "- **Canada:** IRCC open data, admissions of permanent residents by country of citizenship "
        "and immigration category, January 2015 to September 2026. IRCC rounds to the nearest 5.\n"
        "- **United Kingdom:** Home Office entry clearance visa outcomes, Jamaican nationals, "
        "2005 to June 2026. Long stay visas exclude visitor visas.\n"
        "- **World Bank:** GDP per person, government spending per student by level, population.\n"
        "- **Bank of Jamaica:** gross remittance inflows.\n"
        "- Counts are of people granted status in a year. Many were already living abroad, and "
        "none of these sources records most people's jobs."
    )
    st.download_button("Download the annual data (CSV)", panel.to_csv().encode(),
                       "jamaica_emigration_panel.csv", "text/csv")
