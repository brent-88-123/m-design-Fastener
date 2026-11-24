import math
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bolted Joint Calculator", layout="wide")

# --- 1. CENTRALIZED MATERIAL DATABASE ---
MATERIAL_DB = {
    "Steel S235JR (Structural)": {"E_mpa": 210000.0, "tau_shear_mpa": 210.0, "alpha_1e6": 12.0, "crush_mpa": 235.0},
    "Steel S355J2 (High-Strength)": {"E_mpa": 210000.0, "tau_shear_mpa": 280.0, "alpha_1e6": 12.0, "crush_mpa": 355.0},
    "Steel 42CrMo4 (Alloy)": {"E_mpa": 210000.0, "tau_shear_mpa": 520.0, "alpha_1e6": 11.5, "crush_mpa": 650.0},
    "Stainless Steel A2-70 / 304": {"E_mpa": 195000.0, "tau_shear_mpa": 320.0, "alpha_1e6": 16.0, "crush_mpa": 450.0},
    "Cast Iron EN-GJL-250 (Gray)": {"E_mpa": 105000.0, "tau_shear_mpa": 160.0, "alpha_1e6": 10.5, "crush_mpa": 250.0},
    "Ductile Iron EN-GJS-400": {"E_mpa": 170000.0, "tau_shear_mpa": 260.0, "alpha_1e6": 11.0, "crush_mpa": 400.0},
    "Aluminum EN AW-6061-T6": {"E_mpa": 69000.0, "tau_shear_mpa": 170.0, "alpha_1e6": 23.6, "crush_mpa": 275.0},
    "Aluminum EN AW-7075-T6": {"E_mpa": 72000.0, "tau_shear_mpa": 280.0, "alpha_1e6": 23.4, "crush_mpa": 500.0},
    "Brass CuZn39Pb3": {"E_mpa": 100000.0, "tau_shear_mpa": 220.0, "alpha_1e6": 20.0, "crush_mpa": 290.0},
}

BOLT_GRADES = {
    "4.6": {"Rp02": 240.0, "Rm": 400.0, "tau_shear": 240.0, "E": 210000.0, "alpha_1e6": 12.0},
    "5.8": {"Rp02": 400.0, "Rm": 500.0, "tau_shear": 300.0, "E": 210000.0, "alpha_1e6": 12.0},
    "8.8": {"Rp02": 640.0, "Rm": 800.0, "tau_shear": 480.0, "E": 210000.0, "alpha_1e6": 12.0},
    "10.9": {"Rp02": 900.0, "Rm": 1000.0, "tau_shear": 600.0, "E": 210000.0, "alpha_1e6": 11.5},
    "12.9": {"Rp02": 1080.0, "Rm": 1200.0, "tau_shear": 720.0, "E": 210000.0, "alpha_1e6": 11.5},
    "A2-70 (Stainless)": {"Rp02": 450.0, "Rm": 700.0, "tau_shear": 420.0, "E": 195000.0, "alpha_1e6": 16.0},
    "A2-90 (High-Strength A2)": {"Rp02": 700.0, "Rm": 900.0, "tau_shear": 540.0, "E": 195000.0, "alpha_1e6": 16.0},
}

# Screw / head profiles:
# dw_mult: effective bearing diameter multiplier relative to nominal d
# head_h_mult: approximate head height multiplier for head-shank shear area
# cone_factor: increases effective friction torque slightly for 90-deg countersunk heads
HEAD_TYPES = {
    "Hex Head": {"dw_mult": 1.50, "head_h_mult": 0.65, "cone_factor": 1.00},
    "Socket Cap (ISO 4762)": {"dw_mult": 1.38, "head_h_mult": 1.00, "cone_factor": 1.00},
    "Button Head (ISO 7380)": {"dw_mult": 1.55, "head_h_mult": 0.50, "cone_factor": 1.05},
    "Countersunk 90° (ISO 10642)": {"dw_mult": 1.45, "head_h_mult": 0.45, "cone_factor": 1.35},
}

THREAD_DATA = {
    2.0: {"p": 0.40, "As": 2.07, "label": "M2"},
    2.5: {"p": 0.45, "As": 3.39, "label": "M2.5"},
    3.0: {"p": 0.50, "As": 5.03, "label": "M3"},
    4.0: {"p": 0.70, "As": 8.78, "label": "M4"},
    5.0: {"p": 0.80, "As": 14.20, "label": "M5"},
    6.0: {"p": 1.00, "As": 20.10, "label": "M6"},
    8.0: {"p": 1.25, "As": 36.60, "label": "M8"},
    10.0: {"p": 1.50, "As": 58.00, "label": "M10"},
    12.0: {"p": 1.75, "As": 84.30, "label": "M12"},
    16.0: {"p": 2.00, "As": 157.00, "label": "M16"},
    20.0: {"p": 2.50, "As": 245.00, "label": "M20"},
    24.0: {"p": 3.00, "As": 353.00, "label": "M24"},
}

CONDITIONS = {
    "Dry / As-Received": (0.14, 0.14),
    "Lubricated / Anti-Seize": (0.10, 0.12),
    "Liquid Thread Locker": (0.12, 0.13),
    "Stainless / Galling Risk": (0.22, 0.20),
}

st.title("Bolted & Screwed Joint Calculator")

# --- 2. COMPACT TOP INPUTS ---
r1_c1, r1_c2, r1_c3, r1_c4, r1_c5, r1_c6 = st.columns([0.9, 1.3, 1.4, 1.3, 1.4, 1.1])
with r1_c1:
    thread_size = st.selectbox(
        "Thread",
        list(THREAD_DATA.keys()),
        index=5,
        format_func=lambda x: THREAD_DATA[x]["label"],
    )
with r1_c2:
    bolt_grade = st.selectbox("Grade", list(BOLT_GRADES.keys()), index=2)
with r1_c3:
    head_type = st.selectbox("Screw / Head", list(HEAD_TYPES.keys()), index=1)
with r1_c4:
    joint_type = st.selectbox("Joint Type", ["Through-Bolt + Nut", "Screwed into Tapped Plate"])
with r1_c5:
    condition = st.selectbox("Surface / Additive", list(CONDITIONS.keys()) + ["Custom"])
with r1_c6:
    utilization = st.slider("Yield Factor (nu)", 0.50, 0.95, 0.85, 0.05)

r2_c1, r2_c2, r2_c3, r2_c4, r2_c5, r2_c6 = st.columns([1.1, 1.1, 1.0, 1.0, 1.1, 1.5])
with r2_c1:
    load_mean_n = st.number_input("Mean Load Fa (N)", min_value=0.0, value=500.0, step=50.0)
with r2_c2:
    load_alt_n = st.number_input("Alt. Amp ±Fa (N)", min_value=0.0, value=200.0, step=25.0)
with r2_c3:
    delta_t_c = st.number_input("Temp ΔT (°C)", min_value=-200.0, max_value=600.0, value=0.0, step=10.0)
with r2_c4:
    num_plates = st.selectbox("Plates", [1, 2, 3, 4], index=2)
with r2_c5:
    engage_mm = st.number_input(
        "Tap Depth (mm)",
        min_value=1.0,
        value=8.0,
        step=1.0,
        disabled=(joint_type == "Through-Bolt + Nut"),
    )
with r2_c6:
    if condition == "Custom":
        fc1, fc2 = st.columns(2)
        mu_th = fc1.number_input("mu_th", 0.04, 0.40, 0.12, 0.01)
        mu_hd = fc2.number_input("mu_hd", 0.04, 0.40, 0.12, 0.01)
    else:
        mu_th, mu_hd = CONDITIONS[condition]
        st.caption(f"Friction: mu_th = {mu_th:.2f}, mu_hd = {mu_hd:.2f}")

mat_names = list(MATERIAL_DB.keys())
default_mats = [
    "Aluminum EN AW-6061-T6",
    "Aluminum EN AW-7075-T6",
    "Steel S355J2 (High-Strength)",
    "Steel S235JR (Structural)",
]
default_thick = [4.0, 5.0, 8.0, 6.0]

plates = []
p_cols = st.columns(num_plates)
for idx in range(num_plates):
    with p_cols[idx]:
        c_mat, c_thk = st.columns([2.2, 1.0])
        m_choice = c_mat.selectbox(
            f"Plate {idx + 1} Mat.",
            mat_names,
            index=mat_names.index(default_mats[idx]),
            key=f"p_mat_{idx}",
        )
        t_val = c_thk.number_input(
            f"t{idx + 1} (mm)",
            min_value=0.5,
            value=default_thick[idx],
            step=0.5,
            key=f"p_thk_{idx}",
        )
        plates.append((m_choice, t_val))

# --- 3. ENGINEERING CALCULATIONS ---
t_label = THREAD_DATA[thread_size]["label"]
d = float(thread_size)
p = THREAD_DATA[thread_size]["p"]
As = THREAD_DATA[thread_size]["As"]
Rp02 = BOLT_GRADES[bolt_grade]["Rp02"]
Rm = BOLT_GRADES[bolt_grade]["Rm"]
tau_bolt_shear = BOLT_GRADES[bolt_grade]["tau_shear"]
E_bolt = BOLT_GRADES[bolt_grade]["E"]
alpha_bolt = BOLT_GRADES[bolt_grade]["alpha_1e6"] * 1e-6

dw_mult = HEAD_TYPES[head_type]["dw_mult"]
head_h_mult = HEAD_TYPES[head_type]["head_h_mult"]
cone_factor = HEAD_TYPES[head_type]["cone_factor"]

through_thickness = sum(t for _, t in plates)
Lk = through_thickness + (0.5 * engage_mm if joint_type == "Screwed into Tapped Plate" else 0.0)

# Preload FM (N) and tightening torque T (N*m) using head bearing diameter dw
FM_n = utilization * As * Rp02
d2 = d - 0.6495 * p
dw = dw_mult * d
T_nm = (FM_n * (0.16 * p + 0.583 * d2 * mu_th + 0.5 * dw * mu_hd * cone_factor)) / 1000.0

# Bolt stiffness Cs (N/mm) and multi-plate series stiffness Cp (N/mm)
Cs = (E_bolt * As) / Lk

inv_Cp = 0.0
weighted_plate_elong_per_dt = 0.0
total_eff_plate_len = 0.0

for idx, (m_name, t_val) in enumerate(plates):
    eff_t = t_val + (0.5 * engage_mm if (joint_type == "Screwed into Tapped Plate" and idx == num_plates - 1) else 0.0)
    d_eff = dw + 0.5 * eff_t
    Ap = (math.pi / 4.0) * max((d_eff * 1.4) ** 2 - d**2, 2.0)
    E_p = MATERIAL_DB[m_name]["E_mpa"]
    alpha_p = MATERIAL_DB[m_name]["alpha_1e6"] * 1e-6

    Cp_i = (E_p * Ap) / eff_t
    inv_Cp += 1.0 / Cp_i

    weighted_plate_elong_per_dt += eff_t * alpha_p
    total_eff_plate_len += eff_t

Cp = 1.0 / inv_Cp if inv_Cp > 0 else 1e9
Phi = Cs / (Cs + Cp)

# Thermal preload shift dF_th (N)
alpha_plate_eq = weighted_plate_elong_per_dt / total_eff_plate_len if total_eff_plate_len > 0 else alpha_bolt
delta_F_th_n = ((Cs * Cp) / (Cs + Cp)) * delta_t_c * (alpha_plate_eq - alpha_bolt) * Lk
FM_op_n = FM_n + delta_F_th_n

# Operating loads and stresses
F_mean_n = FM_op_n + Phi * load_mean_n
F_max_n = F_mean_n + Phi * load_alt_n
sigma_mean = F_mean_n / As
sigma_max = F_max_n / As
sigma_amp = (Phi * load_alt_n) / As

d3 = d - 1.2268 * p
Wp = (math.pi * (d3**3)) / 16.0
tau_t = ((T_nm * 1000.0) * (0.583 * d2 / 2.0)) / Wp if Wp > 0 else 0.0
sigma_v_max = math.sqrt(sigma_max**2 + 3.0 * (tau_t**2))
sf_yield = Rp02 / sigma_v_max if sigma_v_max > 0 else float("inf")

residual_clamp_n = FM_op_n - (1.0 - Phi) * (load_mean_n + load_alt_n)

if load_alt_n > 0:
    sigma_endurance = 55.0 if bolt_grade in ["10.9", "12.9", "A2-90 (High-Strength A2)"] else 45.0
    denom = (sigma_amp / sigma_endurance) + (sigma_mean / Rm)
    sf_fatigue = (1.0 / denom) if denom > 0 else float("inf")
else:
    sf_fatigue = float("inf")

# Under-head crushing check on Plate 1 (under screw/bolt head)
A_bearing_head = max((math.pi / 4.0) * (dw**2 - d**2), 0.5)
p_crush_mpa = FM_op_n / A_bearing_head
top_plate_crush_allow = MATERIAL_DB[plates[0][0]]["crush_mpa"]
sf_head_crush = (top_plate_crush_allow / p_crush_mpa) if p_crush_mpa > 0 else float("inf")

# Head shear-off check (approximate cylindrical shear around shank/head root)
head_h_mm = head_h_mult * d
A_head_shear = math.pi * d * head_h_mm
tau_head_actual = F_max_n / A_head_shear if A_head_shear > 0 else 0.0
sf_head_shear = (tau_bolt_shear / tau_head_actual) if tau_head_actual > 0 else float("inf")
sf_head_governing = min(sf_head_crush, sf_head_shear)

# Thread stripping / shear check (internal vs. external thread shear)
d1 = d - 1.0825 * p
if joint_type == "Screwed into Tapped Plate":
    last_mat = plates[-1][0]
    tau_internal_allow = MATERIAL_DB[last_mat]["tau_shear_mpa"]
    A_shear_int = math.pi * d1 * engage_mm * 0.5
    tau_int_actual = F_max_n / A_shear_int if A_shear_int > 0 else 0.0
    sf_thread_int = (tau_internal_allow / tau_int_actual) if tau_int_actual > 0 else float("inf")

    A_shear_ext = math.pi * d2 * engage_mm * 0.5
    tau_ext_actual = F_max_n / A_shear_ext if A_shear_ext > 0 else 0.0
    sf_thread_ext = (tau_bolt_shear / tau_ext_actual) if tau_ext_actual > 0 else float("inf")

    sf_thread_governing = min(sf_thread_int, sf_thread_ext)
    thread_limit_desc = f"Tapped ({last_mat}) SF: {sf_thread_int:.2f} | Screw thread SF: {sf_thread_ext:.2f}"
else:
    nut_engage = 0.8 * d
    A_shear_ext = math.pi * d2 * nut_engage * 0.5
    tau_ext_actual = F_max_n / A_shear_ext if A_shear_ext > 0 else 0.0
    sf_thread_ext = (tau_bolt_shear / tau_ext_actual) if tau_ext_actual > 0 else float("inf")
    sf_thread_governing = sf_thread_ext
    thread_limit_desc = f"Nut/screw thread (~{nut_engage:.1f} mm) shear SF: {sf_thread_ext:.2f}"

head_limit_desc = (
    f"Plate 1 crush ({plates[0][0]}) SF: {sf_head_crush:.2f} ({p_crush_mpa:.0f} MPa) | "
    f"Head shear SF: {sf_head_shear:.2f}"
)

# Compare the three static failure mechanisms
modes = {
    "Screw/Bolt Shank Yielding": sf_yield,
    "Thread Stripping / Shear": sf_thread_governing,
    "Head Bearing Crush / Shear": sf_head_governing,
}
dominant_mode = min(modes, key=modes.get)

# --- 4. COMPACT OUTPUT & CSV EXPORT ---
m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Preload FM", f"{FM_n:,.0f} N", delta=f"{delta_F_th_n:+,.0f} N ΔT")
m2.metric("Torque T", f"{T_nm:.2f} N·m")
m3.metric("Load Factor Phi", f"{Phi:.3f}")
m4.metric("Shank Yield SF", f"{sf_yield:.2f}")
m5.metric("Thread Shear SF", f"{sf_thread_governing:.2f}")
m6.metric("Head SF", f"{sf_head_governing:.2f}")
m7.metric("Fatigue SF", f"{sf_fatigue:.2f}" if load_alt_n > 0 else "N/A")

o1, o2, o3 = st.columns([1.6, 1.5, 0.9])
with o1:
    st.write(f"**dw:** {dw:.1f} mm | **Lk:** {Lk:.1f} mm | **Cs:** {Cs:,.0f} N/mm | **Cp:** {Cp:,.0f} N/mm")
    st.write(f"**Residual Clamp:** {residual_clamp_n:,.0f} N | **Max v. Mises:** {sigma_v_max:.1f} MPa")
    st.caption(f"{thread_limit_desc} | {head_limit_desc}")
with o2:
    st.write(f"**Lowest static SF mode:** {dominant_mode} ({modes[dominant_mode]:.2f})")
    if FM_op_n <= 0 or residual_clamp_n <= 0:
        st.error("Preload loss / joint separation risk: residual clamp <= 0 N.")
    elif min(sf_yield, sf_thread_governing, sf_head_governing) < 1.2 or (load_alt_n > 0 and sf_fatigue < 1.5):
        st.warning(f"Low margin — most critical mode: {dominant_mode}.")
    else:
        st.success("Joint clamped; static and fatigue margins look healthy.")
with o3:
    report_df = pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Thread": t_label,
        "Bolt_Grade": bolt_grade,
        "Head_Type": head_type,
        "Joint_Type": joint_type,
        "Delta_T_C": delta_t_c,
        "Thermal_Preload_Shift_N": round(delta_F_th_n, 1),
        "Op_Preload_N": round(FM_op_n, 1),
        "Torque_Nm": round(T_nm, 3),
        "Load_Factor_Phi": round(Phi, 3),
        "Shank_Yield_SF": round(sf_yield, 2) if sf_yield != float("inf") else "inf",
        "Thread_Shear_SF": round(sf_thread_governing, 2) if sf_thread_governing != float("inf") else "inf",
        "Head_SF": round(sf_head_governing, 2) if sf_head_governing != float("inf") else "inf",
        "Lowest_Static_Mode": dominant_mode,
        "Fatigue_SF": round(sf_fatigue, 2) if (load_alt_n > 0 and sf_fatigue != float("inf")) else "N/A",
    }])
    st.download_button(
        "Download CSV",
        data=report_df.to_csv(index=False).encode("utf-8"),
        file_name=f"joint_{t_label}_{bolt_grade.split()[0]}.csv",
        mime="text/csv",
    )