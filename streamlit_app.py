import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Gross to Net Pay Calculator | Expats", layout="wide")

# ---------------- Helpers ----------------
def fmt0(x):
    try:
        return f"{x:,.0f}"
    except Exception:
        return str(x)

def sanitize_brackets(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure rates are decimals (0-1), sort by cap, append terminal None row."""
    if df is None or len(df) == 0:
        return pd.DataFrame([{"Upper_Limit": None, "Rate": 0.0}])
    out = df.copy()
    out["Rate"] = out["Rate"].apply(lambda r: r/100.0 if (r is not None and r > 1) else (r or 0.0))
    out = out.sort_values(by=["Upper_Limit"], key=lambda s: s.fillna(np.inf)).reset_index(drop=True)
    if out["Upper_Limit"].isna().sum() == 0:
        last_rate = float(out["Rate"].iloc[-1]) if len(out) > 0 else 0.0
        out.loc[len(out)] = [None, last_rate]
    return out

def apply_progressive(df: pd.DataFrame, amount: float):
    """Return (tax, rows) where rows show slab breakdown."""
    if amount <= 0:
        return 0.0, []
    df = sanitize_brackets(df)
    rem = amount
    prev_cap = 0.0
    tax = 0.0
    rows = []
    for _, r in df.iterrows():
        cap = r["Upper_Limit"]
        rate = float(r["Rate"]) if not pd.isna(r["Rate"]) else 0.0
        if cap is None:
            slab_amt = max(0.0, rem)
        else:
            slab_amt = max(0.0, min(rem, cap - prev_cap))
        slab_tax = slab_amt * rate
        if slab_amt > 0:
            rows.append({
                "From": prev_cap,
                "To": cap if cap is not None else "∞",
                "Rate": rate,
                "Amount": slab_amt,
                "Tax": slab_tax
            })
        tax += slab_tax
        rem -= slab_amt
        prev_cap = cap if cap is not None else prev_cap
        if rem <= 0:
            break
    return tax, rows

# ---------------- Sidebar ----------------
st.sidebar.title("Settings")
country = st.sidebar.selectbox(
    "Country of work",
    ["Korea", "Taiwan", "Singapore", "Japan", "India", "United States"],
    index=2
)

show_usd = st.sidebar.checkbox("Show USD equivalents", value=True)
enable_export = st.sidebar.checkbox("Enable CSV export", value=True)

us_overlay_allowed = (country != "United States")
us_overlay = st.sidebar.checkbox(
    "US Citizen/ GC Holder",
    value=False,
    disabled=(not us_overlay_allowed)
)

# FX per USD (local per USD)
fx_defaults = {"Korea": 1350.0, "Taiwan": 32.0, "Singapore": 1.35, "Japan": 155.0, "India": 84.0, "United States": 1.0}
fx_labels   = {"Korea": "FX (KRW per USD)", "Taiwan": "FX (NTD per USD)", "Singapore": "FX (SGD per USD)",
               "Japan": "FX (JPY per USD)", "India": "FX (INR per USD)", "United States": "FX (USD per USD)"}
fx = st.sidebar.number_input(
    fx_labels[country],
    min_value=0.0001,
    value=float(fx_defaults[country]),
    step=0.01,
    format="%.4f",
    disabled=(country == "United States")
)

st.sidebar.markdown("---")
st.sidebar.markdown("**US Overlay Defaults**")
feie = st.sidebar.number_input("FEIE (USD)", min_value=0.0, value=126500.0, step=500.0, disabled=(not us_overlay_allowed))
std_ded = st.sidebar.number_input("Standard deduction (USD)", min_value=0.0, value=14600.0, step=100.0, disabled=(not us_overlay_allowed))

st.sidebar.caption("US Brackets (enter rates as decimals, e.g., 0.22)")
us_brackets_default = pd.DataFrame({
    "Upper_Limit": [11600.0, 47150.0, 100525.0, 191950.0, 243725.0, 609350.0, None],
    "Rate":        [0.10,    0.12,     0.22,     0.24,     0.32,     0.35,     0.37]
})
us_brackets = st.sidebar.data_editor(us_brackets_default, num_rows="dynamic", use_container_width=True, key="us_br")

# ---------------- Title ----------------
st.title("Gross to Net Pay Calculator | Expats")
st.caption("Estimates only — excludes social insurance, surcharges, cess, and detailed rules. For precise calculations, consult a qualified tax advisor.")

# ---------------- Inputs ----------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    base = st.number_input("Base Pay", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
with c2:
    var_pct = st.number_input("Variable % of Base", min_value=0.0, value=0.0, step=1.0, format="%.0f")
with c3:
    crsu = st.number_input("Y1 CRSU", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
with c4:
    signon = st.number_input("Joining Bonus (if any)", min_value=0.0, value=0.0, step=1000.0, format="%.0f")
with c5:
    y1_rsu = st.number_input("Y1 RSU Value", min_value=0.0, value=0.0, step=1000.0, format="%.0f")

variable_amt = base * (var_pct / 100.0)
earned = base + variable_amt + crsu + signon
total_comp = earned + y1_rsu

st.markdown(f"**Total Comp (excl. Y1 RSU):** {fmt0(earned)}")
st.markdown(f"**Total Comp (incl. Y1 RSU):** {fmt0(total_comp)}")

# ---------------- Country Local Layer ----------------
local_tax = 0.0
local_net = total_comp

# For overlay calcs (always derive USD from gross earned/RSU, not country exemptions)
earned_usd = 0.0
rsu_usd = 0.0
local_tax_usd = 0.0
local_net_usd = 0.0

def show_local(currency_label, tax_value, net_value, fx_to_usd):
    colA, colB = st.columns(2)
    with colA:
        st.metric(f"Local Tax ({currency_label})", fmt0(tax_value))
        st.metric(f"Net After Local Tax ({currency_label})", fmt0(net_value))
    if show_usd and fx_to_usd > 0:
        with colB:
            st.metric("Local Tax (USD)", fmt0(tax_value / fx_to_usd))
            st.metric("Net After Local Tax (USD)", fmt0(net_value / fx_to_usd))

if country == "Korea":
    currency = "KRW"
    st.subheader("Korea")
    local_tax = total_comp * 0.21
    local_net = total_comp - local_tax
    show_local(currency, local_tax, local_net, fx)
    if fx > 0:
        earned_usd, rsu_usd = earned / fx, y1_rsu / fx
        local_tax_usd, local_net_usd = local_tax / fx, local_net / fx

elif country == "Taiwan":
    currency = "NTD"
    st.subheader("Taiwan: 50% of earnings (excl. RSUs) > 3M NTD is Tax Exempt")
    tw_default = pd.DataFrame({"Upper_Limit":[590000.0,1330000.0,2660000.0,4980000.0,None],
                               "Rate":[0.05,0.12,0.20,0.30,0.40]})
    tw_brackets = st.data_editor(tw_default, num_rows="dynamic", use_container_width=True, key="tw_br")
    # Local layer uses the 50% exemption above 3M on earned
    above = max(earned - 3_000_000.0, 0.0)
    exempt = 0.5 * above
    taxable_earned = max(earned - exempt, 0.0)
    taxable_total = taxable_earned + y1_rsu
    local_tax, detail = apply_progressive(tw_brackets, taxable_total)
    local_net = total_comp - local_tax
    show_local(currency, local_tax, local_net, fx)
    if fx > 0:
        # IMPORTANT: For US overlay, use GROSS earned & RSU converted to USD (not Taiwan-exempted amounts)
        earned_usd, rsu_usd = earned / fx, y1_rsu / fx
        local_tax_usd, local_net_usd = local_tax / fx, local_net / fx

elif country == "Singapore":
    currency = "SGD"
    st.subheader("Singapore")
    sg_default = pd.DataFrame({
        "Upper_Limit":[20000,30000,40000,80000,120000,160000,200000,240000,280000,320000,500000,1000000,None],
        "Rate":[0.00,0.02,0.035,0.07,0.115,0.15,0.18,0.19,0.195,0.20,0.22,0.23,0.24]
    })
    sg_brackets = st.data_editor(sg_default, num_rows="dynamic", use_container_width=True, key="sg_br")
    local_tax, detail = apply_progressive(sg_brackets, total_comp)
    local_net = total_comp - local_tax
    show_local(currency, local_tax, local_net, fx)
    if fx > 0:
        earned_usd, rsu_usd = earned / fx, y1_rsu / fx
        local_tax_usd, local_net_usd = local_tax / fx, local_net / fx

elif country == "Japan":
    currency = "JPY"
    st.subheader("Japan")
    jp_default = pd.DataFrame({"Upper_Limit":[1950000,3300000,6950000,9000000,18000000,40000000,None],
                               "Rate":[0.05,0.10,0.20,0.23,0.33,0.40,0.45]})
    jp_brackets = st.data_editor(jp_default, num_rows="dynamic", use_container_width=True, key="jp_br")
    local_tax, detail = apply_progressive(jp_brackets, total_comp)
    local_net = total_comp - local_tax
    show_local(currency, local_tax, local_net, fx)
    if fx > 0:
        earned_usd, rsu_usd = earned / fx, y1_rsu / fx
        local_tax_usd, local_net_usd = local_tax / fx, local_net / fx

elif country == "India":
    currency = "INR"
    st.subheader("India: New Regime (incl. surcharge & cess)")
    in_default = pd.DataFrame({
        "Upper_Limit":[400000,800000,1200000,1600000,2000000,2400000,None],
        "Rate":[0.00,0.05,0.10,0.15,0.20,0.25,0.30]
    })
    in_brackets = st.data_editor(in_default, num_rows="dynamic", use_container_width=True, key="in_br")

    # 1) Base income tax from slabs (on total_comp = earned + RSU)
    base_tax, detail = apply_progressive(in_brackets, total_comp)

    # 2) Surcharge (new regime): 10% >50L–1Cr, 15% >1Cr–2Cr, 25% >2Cr
    ti = float(total_comp)  # total income in INR
    if     ti > 20_000_000:
        sur_rate = 0.25
    elif   ti > 10_000_000:
        sur_rate = 0.15
    elif   ti > 5_000_000:
        sur_rate = 0.10
    else:
        sur_rate = 0.0
    surcharge = base_tax * sur_rate

    # 3) Health & Education Cess = 4% of (tax + surcharge)
    cess = 0.04 * (base_tax + surcharge)

    # 4) Local totals
    local_tax = base_tax + surcharge + cess
    local_net = total_comp - local_tax

    # Show summary
    show_local(currency, local_tax, local_net, fx)

    # Optional detail (expand if you want a breakdown)
    with st.expander("India tax breakdown"):
        st.write({
            "Base tax": fmt0(base_tax),
            "Surcharge rate": f"{sur_rate:.0%}",
            "Surcharge": fmt0(surcharge),
            "Cess (4%)": fmt0(cess),
            "Total India tax": fmt0(local_tax)
        })

    # USD views for overlay math
    if fx > 0:
        earned_usd, rsu_usd = earned / fx, y1_rsu / fx
        local_tax_usd, local_net_usd = local_tax / fx, local_net / fx

elif country == "United States":
    currency = "USD"
    st.subheader("United States")
    local_tax, detail = apply_progressive(us_brackets, total_comp)
    local_net = total_comp - local_tax
    show_local(currency, local_tax, local_net, 1.0)
    earned_usd, rsu_usd = earned, y1_rsu
    local_tax_usd, local_net_usd = local_tax, local_net

# ---------------- US Overlay ----------------
st.markdown("---")
overlay_title = "US Overlay"
if country == "United States":
    st.header(f"{overlay_title} (Disabled for US work country)")
    st.info("Overlay disabled because country of work is United States")
else:
    st.header(f"{overlay_title} {'(ON)' if us_overlay else '(OFF)'}")
    if us_overlay:
        if fx <= 0:
            st.error("FX must be greater than zero for USD calculations.")
        else:
            # FEIE applies to earned + RSU (per your requirement)
            us_taxable = max((earned_usd + rsu_usd) - feie - std_ded, 0.0)
            us_tax, us_rows = apply_progressive(us_brackets, us_taxable)
            # Simplified FTC cap: limited to US tentative tax
            ftc = min(local_tax_usd, us_tax)
            us_due = max(us_tax - ftc, 0.0)
            combined_tax = local_tax_usd + us_due
            combined_net = (earned_usd + rsu_usd) - combined_tax

            cL, cR = st.columns(2)
            with cL:
                st.metric("US Tentative Tax (USD)", fmt0(us_tax))
                st.metric("Foreign Tax Credit used (USD)", fmt0(ftc))
                st.metric("US Tax Due (USD)", fmt0(us_due))
            with cR:
                st.metric("Combined Tax (USD)", fmt0(combined_tax))
                st.metric("Net After All Taxes (USD)", fmt0(combined_net))

            with st.expander("Overlay details & slabs"):
                st.write(f"Earned USD (gross): {fmt0(earned_usd)}  |  RSU USD: {fmt0(rsu_usd)}")
                st.write(f"US Taxable = Earned_USD + RSU_USD − FEIE − Std Ded = {fmt0(us_taxable)}")
                st.dataframe(pd.DataFrame(us_rows))

# ---------------- Export ----------------
st.markdown("---")
if enable_export:
    exp = {
        "Country": country, "FX_to_USD": fx,
        "Base": base, "Variable_%": var_pct, "CRSU": crsu, "SignOn": signon, "Y1_RSU": y1_rsu,
        "Earned": earned, "Total_Comp": total_comp,
        "Local_Tax": local_tax, "Net_After_Local": local_net
    }
    df1 = pd.DataFrame([exp]).round(2)
    st.download_button(
        "Download Local Layer CSV",
        data=df1.to_csv(index=False).encode("utf-8"),
        file_name=f"{country}_local_layer.csv",
        mime="text/csv"
    )
