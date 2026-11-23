"""Build the annual panel and summary numbers for the Jamaica brain drain project.

Inputs are the raw files in data/raw (see README for sources). Outputs go to outputs/.
Run: python src/analysis.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)


def num(s):
    """Turn suppressed cells ('--', 'D', '-') into NaN and the rest into numbers."""
    return pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")


def load_us():
    d = pd.read_csv(RAW / "us_lpr_jamaica_born_by_class.csv")
    for c in d.columns[1:]:
        d[c] = num(d[c])
    d = d.rename(columns={"fiscal_year": "year"}).set_index("year")
    d["family_all"] = d.immediate_relatives + d.family_preferences
    return d


def load_canada():
    d = pd.read_csv(RAW / "canada_pr_jamaica_by_category_annual.csv")
    d = d.drop_duplicates("category", keep="last").set_index("category")  # D and C rows repeat
    d = d.drop(columns="level").rename(columns={"2026_jan_sep": "2026"})
    d = d.apply(num).T
    d.index = d.index.astype(int)
    out = pd.DataFrame({
        "total": d["Jamaica - Total"],
        "economic": d["Economic - Total"],
        "family": d["Sponsored Family - Total"],
        "refugee": d["Resettled Refugee & Protected Person in Canada - Total"],
        "other": d["All Other Immigration - Total"],
        "skilled_worker_programs": d["Worker Program"],
        "provincial_nominee": d["Provincial Nominee Program"],
        "caregiver": d["Caregiver"],
    })
    return out


def load_uk():
    v = pd.read_csv(RAW / "uk_entry_visas_jamaica_issued.csv")
    longstay = v[~v.visa_group.isin(["Visitor"])]
    g = longstay.pivot_table(index="year", columns="visa_group", values="issued", aggfunc="sum").fillna(0)
    g["long_stay_total"] = g.sum(axis=1)
    w = pd.read_csv(RAW / "uk_worker_visas_jamaica.csv")
    hc = w[w.visa_subtype == "Health and Care Worker"].pivot_table(
        index="year", columns="applicant", values="issued", aggfunc="sum").fillna(0)
    sw = w[w.visa_subtype.isin(["Skilled Worker", "Tier 2 - General"])].pivot_table(
        index="year", columns="applicant", values="issued", aggfunc="sum").fillna(0)
    g["health_care_main"] = hc.get("Main Applicant", 0)
    g["health_care_dependants"] = hc.get("Dependant", 0)
    g["skilled_worker_main"] = sw.get("Main Applicant", 0)
    return g.fillna(0)


def load_remittances():
    r = pd.read_csv(RAW / "boj_inbound_by_corridor.csv")
    r["year"] = r.month.str[:4].astype(int)
    counts = r.groupby("year").month.count()
    a = r.groupby("year")[["united_states", "united_kingdom", "canada", "total_remittances"]].sum()
    a = a[counts == 12]
    return a  # US$ millions


def load_wb():
    return pd.read_csv(RAW / "worldbank_jamaica_indicators.csv").set_index("year")


def education_cost(wb, gdp_year=2025):
    """Public spending to educate one person, in current US$.

    Uses the latest World Bank spending per student at each level (% of GDP per
    person) times GDP per person in gdp_year. Years in school: 6 primary,
    5 secondary, 4 tertiary.
    """
    def latest(col):
        s = wb[col].dropna()
        return float(s.iloc[-1]), int(s.index[-1])

    gdp = float(wb.loc[gdp_year, "NY.GDP.PCAP.CD"])
    p, py = latest("SE.XPD.PRIM.PC.ZS")
    s, sy = latest("SE.XPD.SECO.PC.ZS")
    t, ty = latest("SE.XPD.TERT.PC.ZS")
    per_year = {"primary": p / 100 * gdp, "secondary": s / 100 * gdp, "tertiary": t / 100 * gdp}
    return {
        "gdp_per_person": gdp,
        "gdp_year": gdp_year,
        "share_primary_pct": p, "share_primary_year": py,
        "share_secondary_pct": s, "share_secondary_year": sy,
        "share_tertiary_pct": t, "share_tertiary_year": ty,
        "per_year": per_year,
        "school_leaver": 6 * per_year["primary"] + 5 * per_year["secondary"],
        "graduate": 6 * per_year["primary"] + 5 * per_year["secondary"] + 4 * per_year["tertiary"],
    }


def main():
    us, ca, uk, rem, wb = load_us(), load_canada(), load_uk(), load_remittances(), load_wb()

    years = range(2014, 2027)
    panel = pd.DataFrame(index=pd.Index(years, name="year"))
    panel["us_green_cards"] = us.total
    panel["us_employment_based"] = us.employment
    panel["us_family_based"] = us.family_all
    panel["canada_permanent_residents"] = ca.total
    panel["canada_economic"] = ca.economic
    panel["canada_family"] = ca.family
    panel["uk_long_stay_visas"] = uk.long_stay_total
    panel["uk_work_visas"] = uk.get("Work")
    panel["uk_health_care_main"] = uk.health_care_main
    panel["uk_skilled_worker_main"] = uk.skilled_worker_main
    panel["remit_us_usd_m"] = rem.united_states
    panel["remit_uk_usd_m"] = rem.united_kingdom
    panel["remit_canada_usd_m"] = rem.canada
    panel["remit_total_usd_m"] = rem.total_remittances
    panel["population"] = wb["SP.POP.TOTL"]
    panel["labour_force"] = wb["SL.TLF.TOTL.IN"]
    panel.to_csv(OUT / "panel.csv")

    # Notes on comparability: US is fiscal year (Oct to Sep), Canada and UK calendar
    # year; 2026 is part year for Canada (Jan to Sep) and the UK (Jan to Jun).
    full = panel.loc[2014:2024]
    three = full[["us_green_cards", "canada_permanent_residents"]].sum(axis=1)

    cost = education_cost(wb)

    # Share of permanent movers that came through work routes, 2015 to 2024.
    yrs = list(range(2015, 2025))
    us_work_share = us.loc[yrs, "employment"].sum() / us.loc[yrs, "total"].sum()
    ca_work_share = ca.loc[yrs, "economic"].sum() / ca.loc[yrs, "total"].sum()

    # Permanent movers to US and Canada per 1,000 people, 2024.
    movers_2024 = panel.loc[2024, "us_green_cards"] + panel.loc[2024, "canada_permanent_residents"]

    summary = {
        "us_green_cards": {int(y): int(v) for y, v in us.total.items()},
        "us_2024": int(us.loc[2024, "total"]),
        "us_peak_year": int(us.total.idxmax()),
        "us_work_share_2015_2024_pct": round(100 * us_work_share, 1),
        "canada_total": {int(y): int(v) for y, v in ca.total.dropna().items()},
        "canada_2025": int(ca.loc[2025, "total"]),
        "canada_peak_year": int(ca.loc[2015:2025, "total"].idxmax()),
        "canada_peak": int(ca.loc[2015:2025, "total"].max()),
        "canada_work_share_2015_2024_pct": round(100 * ca_work_share, 1),
        "uk_health_care_main": {int(y): int(v) for y, v in uk.health_care_main.items() if y >= 2020},
        "uk_health_care_peak": int(uk.health_care_main.max()),
        "uk_health_care_peak_year": int(uk.health_care_main.idxmax()),
        "uk_work_visas": {int(y): int(v) for y, v in uk.get("Work").items()},
        "movers_us_canada_2024": int(movers_2024),
        "movers_per_1000_people_2024": round(1000 * movers_2024 / panel.loc[2024, "population"], 1),
        "us_canada_2014_2024_total": int(three.sum()),
        "education_cost": cost,
        "remittances_2025_usd_m": round(float(rem.loc[2025, "total_remittances"]), 1),
        "notes": [
            "US counts are fiscal years (October to September) and count people born in Jamaica.",
            "Canada counts are calendar years and count Jamaican citizens; 2026 is January to September.",
            "UK counts are entry clearance visas issued to Jamaican nationals; 2026 is January to June.",
            "Canada rounds counts to the nearest 5 and suppresses counts under 5.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k not in ("us_green_cards", "canada_total", "uk_work_visas")}, indent=1))


if __name__ == "__main__":
    main()
