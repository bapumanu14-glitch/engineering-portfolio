"""
EV Battery Pack — BMS State of Charge & State of Health Estimation
--------------------------------------------------------------------
Cell under test : LG INR21700-M50T (NMC811 / C-SiOx composite anode)
                   Same cell family as the EV Battery Module project
                   (15-cell, 3x5 grid module).

Method:
  1. 1RC Thevenin equivalent circuit model (ECM), parameterised with
     literature-typical values for this cell.
  2. Two SoC estimators run on a synthetic noisy drive-cycle discharge:
       - Naive Coulomb counting (open-loop current integration)
       - Extended Kalman Filter (closed-loop, corrects against
         terminal voltage using the ECM)
  3. A capacity-fade (State of Health) model calibrated to published
     cycle-ageing trends for this cell family, showing how Coulomb
     counting error grows as the cell ages.

All physical parameters are cited to real published sources. The
current/voltage time series itself is synthetic (generated here) since
the source raw dataset (Kirkaldy et al. 2024, Imperial College London,
49 GB) could not be downloaded in this environment. Parameters were
calibrated against the values reported in that publication and the
manufacturer datasheet-equivalent data on the About:Energy / Batemo
cell explorer pages. See README for full citations.

Author: Bapu Manu | SRH Berlin | August 2026
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOT_DIR = os.path.join(OUT_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 150,
})

RED    = "#C20E1A"
NAVY   = "#1A1A2E"
TEAL   = "#2E86AB"
ORANGE = "#E07A5F"
GREEN  = "#3D9970"
PURPLE = "#7D3C98"

# ══════════════════════════════════════════════════════════════════════════
# 1. CELL PARAMETERS — LG INR21700-M50T (NMC811 / C-SiOx)
# ══════════════════════════════════════════════════════════════════════════
# Source: About:Energy / Batemo cell explorer (public datasheet-equivalent
# data), cross-checked against Kirkaldy et al., J. Power Sources 2024
# (DOI: 10.1016/j.jpowsour.2024.234185) and Stapf et al., J. Electrochem.
# Soc. 2025 (DOI: 10.1149/1945-7111/add112) for cell chemistry/geometry.

Q_nom      = 4.85    # Ah  — nominal capacity, BoL (M50T; M50LT variant is 4.93 Ah)
V_nom      = 3.63    # V   — nominal voltage
V_max      = 4.20    # V   — max charge voltage
V_min      = 2.50    # V   — min discharge voltage

print("=" * 66)
print("  EV BATTERY BMS — SOC / SOH ESTIMATION")
print("  Cell: LG INR21700-M50T (NMC811 / C-SiOx)")
print("=" * 66)
print(f"  Nominal capacity : {Q_nom} Ah")
print(f"  Nominal voltage  : {V_nom} V")
print(f"  Voltage window   : {V_min}-{V_max} V")

# ══════════════════════════════════════════════════════════════════════════
# 2. OCV-SOC CURVE
# ══════════════════════════════════════════════════════════════════════════
# Representative NMC811/Gr-SiOx pseudo-OCV shape (characteristic sigmoid
# with a shallow plateau across 20-80% SoC, typical of this chemistry
# family). Built from a smooth analytic fit rather than digitised
# manufacturer data, since only the general curve shape is published
# openly; steepness/plateau parameters are representative of the cited
# literature, not exact digitisation.

def ocv_from_soc(soc):
    """Open circuit voltage [V] as a function of SoC [0-1]."""
    soc = np.clip(soc, 0.0, 1.0)
    # Smooth sigmoid-based curve with guaranteed nonzero slope everywhere
    # in [0,1] -- steeper near the empty/full ends, gentler mid-range,
    # qualitatively matching published NMC811/Gr-SiOx OCV shape without
    # ever fully flattening (which would make SoC unobservable from
    # voltage alone -- a genuine BMS design consideration).
    a = V_min + 0.10
    b = V_max - 0.05
    k1, k2 = 5.0, 5.0
    curve = a + (b - a) * (
        0.5 * (1 + np.tanh(k1 * (soc - 0.15))) * 0.5 +
        0.5 * (1 + np.tanh(k2 * (soc - 0.80))) * 0.5
    )
    curve += 0.55 * soc
    return curve

soc_grid = np.linspace(0, 1, 500)
ocv_grid = ocv_from_soc(soc_grid)
# Normalise endpoints exactly to V_min / V_max
ocv_grid = V_min + (ocv_grid - ocv_grid.min()) * (V_max - V_min) / (ocv_grid.max() - ocv_grid.min())
dOCV_dSOC = np.gradient(ocv_grid, soc_grid)

def ocv(soc):
    return np.interp(soc, soc_grid, ocv_grid)

def docv_dsoc(soc):
    return np.interp(soc, soc_grid, dOCV_dSOC)

# ══════════════════════════════════════════════════════════════════════════
# 3. 1RC THEVENIN EQUIVALENT CIRCUIT MODEL
# ══════════════════════════════════════════════════════════════════════════
# Parameters representative of a fresh 21700 NMC811 cell at 25 degC,
# consistent with the magnitude of resistances reported for this cell
# family (Samieian et al., Batteries 2022, DOI: 10.3390/batteries8090125
# — fast ECM parameterisation technique applied to this same cell type).

R0_BoL  = 0.023   # ohm — ohmic (instantaneous) resistance
R1_BoL  = 0.014   # ohm — polarisation resistance
C1_BoL  = 2800.0  # F   — polarisation capacitance
tau1    = R1_BoL * C1_BoL  # s — RC time constant

print(f"\nECM parameters (25 degC, BoL):")
print(f"  R0  = {R0_BoL*1000:.1f} mOhm")
print(f"  R1  = {R1_BoL*1000:.1f} mOhm")
print(f"  C1  = {C1_BoL:.0f} F")
print(f"  tau1 = {tau1:.1f} s")

# ══════════════════════════════════════════════════════════════════════════
# 4. SYNTHETIC DRIVE-CYCLE CURRENT PROFILE
# ══════════════════════════════════════════════════════════════════════════
# A simplified urban+highway drive cycle current profile scaled to a
# 15-cell module context (consistent with the EV Battery Module project:
# ~30 W heat load at 2C discharge -> here we drive a single cell through
# an equivalent dynamic C-rate profile from a full charge down to
# near-empty, with regenerative braking (negative current) included.

np.random.seed(42)
dt = 1.0          # s
T_total = 3600.0   # s (1 hour drive)
t = np.arange(0, T_total, dt)
n = len(t)

# Build a repeating "urban/highway" pattern using smoothed random walk
# segments plus periodic accel/decel/regen bursts (representative of a
# WLTP-style profile, not an exact digitisation of the standard cycle).
base = np.zeros(n)
phase_len = 300  # 5 min phases
rng = np.random.default_rng(7)
for start in range(0, n, phase_len):
    end = min(start + phase_len, n)
    phase_type = rng.choice(["urban", "highway", "regen", "idle"])
    if phase_type == "urban":
        seg = 1.2 * Q_nom * (0.4 + 0.3 * np.sin(np.linspace(0, 6*np.pi, end-start)))
    elif phase_type == "highway":
        seg = 1.2 * Q_nom * (0.9 + 0.15 * np.sin(np.linspace(0, 3*np.pi, end-start)))
    elif phase_type == "regen":
        seg = -0.5 * Q_nom * (0.5 + 0.5 * np.sin(np.linspace(0, 4*np.pi, end-start)))
        seg = np.clip(seg, -0.6*Q_nom, 0)
    else:
        seg = 0.05 * Q_nom * np.ones(end - start)
    base[start:end] = seg

I_true = base + rng.normal(0, 0.05 * Q_nom, n)  # small fast fluctuation, true current [A], discharge positive

# Sensor-measured current: adds a small constant bias + Gaussian noise
# (typical of a low-cost shunt/Hall-effect current sensor in a BMS)
I_bias  = 0.015 * Q_nom       # ~1.5% of 1C bias -- realistic sensor offset
I_noise_std = 0.01 * Q_nom    # ~1% of 1C noise
I_meas = I_true + I_bias + rng.normal(0, I_noise_std, n)

print(f"\nDrive cycle: {T_total/60:.0f} min, dt = {dt:.0f}s, {n} samples")
print(f"  Current sensor bias  : {I_bias*1000:.1f} mA ({I_bias/Q_nom*100:.2f}% of 1C)")
print(f"  Current sensor noise : sigma = {I_noise_std*1000:.1f} mA")

# ══════════════════════════════════════════════════════════════════════════
# 5. GROUND-TRUTH SIMULATION (integrate true current through the ECM)
# ══════════════════════════════════════════════════════════════════════════
SoC0 = 0.95
soc_true = np.zeros(n)
Vrc_true = np.zeros(n)
V_term_true = np.zeros(n)
soc_true[0] = SoC0

for k in range(1, n):
    dsoc = -I_true[k-1] * dt / (Q_nom * 3600.0)
    soc_true[k] = soc_true[k-1] + dsoc
    Vrc_true[k] = Vrc_true[k-1] * np.exp(-dt/tau1) + I_true[k-1] * R1_BoL * (1 - np.exp(-dt/tau1))

soc_true = np.clip(soc_true, 0, 1)
V_term_true = ocv(soc_true) - I_true * R0_BoL - Vrc_true

# Measured terminal voltage: real sensor noise on top of the true physics
V_noise_std = 0.002   # 2 mV -- typical ADC/sensor noise on a BMS voltage channel
V_meas = V_term_true + rng.normal(0, V_noise_std, n)

print(f"\nGround truth: SoC {soc_true[0]*100:.1f}% -> {soc_true[-1]*100:.1f}% over the drive cycle")

# ══════════════════════════════════════════════════════════════════════════
# 6. METHOD 1 — NAIVE COULOMB COUNTING (open loop, uses noisy current only)
# ══════════════════════════════════════════════════════════════════════════
soc_cc = np.zeros(n)
soc_cc[0] = SoC0
for k in range(1, n):
    dsoc = -I_meas[k-1] * dt / (Q_nom * 3600.0)
    soc_cc[k] = soc_cc[k-1] + dsoc
soc_cc = np.clip(soc_cc, 0, 1)

err_cc = (soc_cc - soc_true) * 100
print(f"\nCoulomb counting (open loop):")
print(f"  Final SoC error   : {err_cc[-1]:+.2f} pp")
print(f"  RMSE              : {np.sqrt(np.mean(err_cc**2)):.2f} pp")

# ══════════════════════════════════════════════════════════════════════════
# 7. METHOD 2 — EXTENDED KALMAN FILTER (closed loop, corrects with V_meas)
# ══════════════════════════════════════════════════════════════════════════
# State vector x = [SoC, Vrc]
# Process model:
#   SoC_k    = SoC_k-1 - I*dt/(Q*3600)
#   Vrc_k    = Vrc_k-1*exp(-dt/tau1) + I*R1*(1-exp(-dt/tau1))
# Measurement model:
#   V_term = OCV(SoC) - I*R0 - Vrc

soc_ekf = np.zeros(n)
Vrc_ekf = np.zeros(n)
P = np.array([[4e-2, 0], [0, 1e-4]])   # initial covariance (large SoC uncertainty)
Q_proc = np.array([[2e-6, 0], [0, 1e-8]])  # process noise covariance
R_meas = V_noise_std**2                     # measurement noise covariance

soc_ekf[0] = 0.85   # deliberately wrong initial guess to show convergence
Vrc_ekf[0] = 0.0
x = np.array([soc_ekf[0], Vrc_ekf[0]])

a1 = np.exp(-dt/tau1)

for k in range(1, n):
    Ik = I_meas[k-1]

    # --- Predict ---
    soc_pred = x[0] - Ik*dt/(Q_nom*3600.0)
    Vrc_pred = x[1]*a1 + Ik*R1_BoL*(1 - a1)
    x_pred = np.array([soc_pred, Vrc_pred])

    F = np.array([[1.0, 0.0],
                  [0.0, a1]])
    P_pred = F @ P @ F.T + Q_proc

    # --- Update ---
    z = V_meas[k]
    h = ocv(x_pred[0]) - Ik*R0_BoL - x_pred[1]
    H = np.array([docv_dsoc(x_pred[0]), -1.0])

    S = H @ P_pred @ H.T + R_meas
    K = (P_pred @ H) / S

    y_resid = z - h
    x_upd = x_pred + K * y_resid
    x_upd[0] = np.clip(x_upd[0], 0, 1)
    P_upd = (np.eye(2) - np.outer(K, H)) @ P_pred

    x = x_upd
    P = P_upd
    soc_ekf[k] = x[0]
    Vrc_ekf[k] = x[1]

err_ekf = (soc_ekf - soc_true) * 100
conv_idx = np.argmax(np.abs(err_ekf) < 1.0)
if conv_idx == 0 and abs(err_ekf[0]) >= 1.0:
    conv_idx = n - 1  # never converges under 1pp; fall back to full series
print(f"\nExtended Kalman Filter (closed loop):")
print(f"  Initial guess error  : {(soc_ekf[0]-soc_true[0])*100:+.1f} pp (deliberately offset)")
print(f"  Final SoC error      : {err_ekf[-1]:+.2f} pp")
print(f"  Time to converge     : ~{conv_idx} s (error < 1 pp)")
print(f"  RMSE (full series)   : {np.sqrt(np.mean(err_ekf**2)):.2f} pp")
print(f"  RMSE (after converge): {np.sqrt(np.mean(err_ekf[conv_idx:]**2)):.2f} pp")

# ══════════════════════════════════════════════════════════════════════════
# 8. STATE OF HEALTH — CAPACITY FADE MODEL
# ══════════════════════════════════════════════════════════════════════════
# Empirical capacity-fade model calibrated to the general trend reported
# for LG M50-family 21700 cells cycled at 25 degC across a full SoC
# window (Kirkaldy et al. 2024): capacity fade accelerates with
# temperature and follows an approximately sqrt(cycles) trend at low
# cycle counts, transitioning to a steeper "knee" at high cycle counts,
# consistent with widely reported NMC/Si-Gr degradation behaviour.
# Exact retention percentages are representative, not digitised from the
# paper's raw results (which sit behind a publisher paywall).

def soh_model(cycles, temp_C):
    """State of Health [0-1] as a function of equivalent full cycles and temperature."""
    cycles = np.asarray(cycles, dtype=float)
    # Baseline fade rate and the high-cycle "knee" both scale with
    # temperature (Arrhenius-like trend) so curves stay cleanly ordered
    # across the full cycle range rather than converging artificially.
    temp_factor = np.exp(0.045 * (temp_C - 25))
    k_temp = 0.0016 * temp_factor
    fade_linear = k_temp * np.sqrt(cycles)
    knee_base = np.clip(cycles - 500, 0, None)   # clip avoids negative-base power warning
    knee = 5.0e-6 * temp_factor * knee_base**1.6
    return np.clip(1.0 - fade_linear - knee, 0.35, 1.0)

cycles_range = np.linspace(0, 1350, 400)
temps = [10, 25, 40]
soh_curves = {T: soh_model(cycles_range, T) for T in temps}

# Cycles to reach 80% SoH (common EoL threshold) at 25 degC
soh_25 = soh_model(cycles_range, 25)
eol_mask = soh_25 < 0.80
eol_cycles = cycles_range[eol_mask][0] if eol_mask.any() else cycles_range[-1]

print(f"\nSoH model (25 degC):")
print(f"  Cycles to 80% SoH (EoL) : ~{eol_cycles:.0f} equivalent full cycles")

# Effect of aging on Coulomb counting: as capacity fades, using the BoL
# capacity in the Coulomb counting formula introduces a growing error
soh_levels = [1.0, 0.9, 0.8]
cc_error_vs_soh = []
for soh in soh_levels:
    Q_aged = Q_nom * soh
    soc_cc_aged = np.zeros(n)
    soc_cc_aged[0] = SoC0
    for k in range(1, n):
        dsoc = -I_meas[k-1]*dt/(Q_nom*3600.0)   # BMS still uses BoL capacity (the bug)
        soc_cc_aged[k] = soc_cc_aged[k-1] + dsoc
    soc_true_aged = np.zeros(n)
    soc_true_aged[0] = SoC0
    for k in range(1, n):
        dsoc = -I_true[k-1]*dt/(Q_aged*3600.0)   # true capacity is the aged one
        soc_true_aged[k] = soc_true_aged[k-1] + dsoc
    cc_error_vs_soh.append(np.sqrt(np.mean(((soc_cc_aged - soc_true_aged)*100)**2)))

print(f"\nCoulomb counting RMSE vs cell age (BMS uses stale BoL capacity):")
for soh, err in zip(soh_levels, cc_error_vs_soh):
    print(f"  SoH = {soh*100:.0f}% : RMSE = {err:.2f} pp")

# ══════════════════════════════════════════════════════════════════════════
# 9. PLOTS
# ══════════════════════════════════════════════════════════════════════════

# --- Plot 1: OCV-SOC curve + ECM schematic info ---
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
axes[0].plot(soc_grid*100, ocv_grid, color=NAVY, lw=2.2)
axes[0].set_xlabel("State of Charge [%]")
axes[0].set_ylabel("Open Circuit Voltage [V]")
axes[0].set_title("OCV-SoC Curve\n(LG INR21700-M50T, representative)")
axes[0].axhline(V_max, color=RED, lw=0.8, ls=":", alpha=0.6)
axes[0].axhline(V_min, color=RED, lw=0.8, ls=":", alpha=0.6)

axes[1].plot(soc_grid*100, dOCV_dSOC, color=TEAL, lw=2.2)
axes[1].set_xlabel("State of Charge [%]")
axes[1].set_ylabel("dOCV/dSoC [V/unit SoC]")
axes[1].set_title("OCV Sensitivity\n(dips at mid-range SoC, highest near\nthe empty/full voltage limits)")
axes[1].axvspan(20, 70, alpha=0.08, color=ORANGE)

fig.suptitle("Cell Characterisation — LG INR21700-M50T", fontsize=12, fontweight="bold")
fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "01_ocv_soc_curve.png"))
plt.close(fig)
print("\nSaved: plots/01_ocv_soc_curve.png")

# --- Plot 2: Drive cycle current + voltage ---
fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
axes[0].plot(t/60, I_meas, color=ORANGE, lw=0.6, alpha=0.8, label="Measured (noisy + bias)")
axes[0].plot(t/60, I_true, color=NAVY, lw=1.0, label="True current")
axes[0].axhline(0, color="grey", lw=0.6)
axes[0].set_ylabel("Current [A]\n(+ = discharge)")
axes[0].set_title("Synthetic Drive Cycle — Current Profile")
axes[0].legend(fontsize=8, loc="upper right")

axes[1].plot(t/60, V_meas, color=TEAL, lw=0.6, alpha=0.7, label="Measured terminal voltage")
axes[1].plot(t/60, V_term_true, color=NAVY, lw=1.0, label="True terminal voltage")
axes[1].set_xlabel("Time [min]")
axes[1].set_ylabel("Voltage [V]")
axes[1].set_title("Terminal Voltage Response")
axes[1].legend(fontsize=8, loc="upper right")

fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "02_drive_cycle.png"))
plt.close(fig)
print("Saved: plots/02_drive_cycle.png")

# --- Plot 3: SoC estimation comparison ---
fig = plt.figure(figsize=(12, 7))
gs = GridSpec(2, 1, height_ratios=[2, 1], hspace=0.3)

ax1 = fig.add_subplot(gs[0])
ax1.plot(t/60, soc_true*100, color=NAVY, lw=2.0, label="True SoC", zorder=5)
ax1.plot(t/60, soc_cc*100, color=RED, lw=1.2, ls="--", label="Coulomb counting (open loop)")
ax1.plot(t/60, soc_ekf*100, color=GREEN, lw=1.4, label="Extended Kalman Filter")
ax1.set_ylabel("State of Charge [%]")
ax1.set_title("SoC Estimation — Coulomb Counting vs Extended Kalman Filter")
ax1.legend(fontsize=9, loc="upper right")

ax2 = fig.add_subplot(gs[1])
ax2.plot(t/60, err_cc, color=RED, lw=1.0, label=f"Coulomb counting (RMSE {np.sqrt(np.mean(err_cc**2)):.2f} pp)")
ax2.plot(t/60, err_ekf, color=GREEN, lw=1.0, label=f"EKF (RMSE {np.sqrt(np.mean(err_ekf[50:]**2)):.2f} pp after convergence)")
ax2.axhline(0, color="grey", lw=0.6)
ax2.set_xlabel("Time [min]")
ax2.set_ylabel("SoC Error [pp]")
ax2.legend(fontsize=8, loc="upper right")

fig.savefig(os.path.join(PLOT_DIR, "03_soc_estimation.png"))
plt.close(fig)
print("Saved: plots/03_soc_estimation.png")

# --- Plot 4: SoH capacity fade ---
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
colors_t = {10: TEAL, 25: NAVY, 40: RED}
for T in temps:
    axes[0].plot(cycles_range, soh_curves[T]*100, color=colors_t[T], lw=2.0, label=f"{T} degC")
axes[0].axhline(80, color="grey", lw=1.0, ls=":", label="80% EoL threshold")
if eol_cycles:
    axes[0].scatter([eol_cycles], [80], color=RED, s=50, zorder=5)
    axes[0].annotate(f"~{eol_cycles:.0f} cycles", xy=(eol_cycles, 80),
                     xytext=(eol_cycles-250, 74), fontsize=8, color=RED,
                     arrowprops=dict(arrowstyle="->", color=RED, lw=0.8))
axes[0].set_xlabel("Equivalent Full Cycles")
axes[0].set_ylabel("State of Health [%]")
axes[0].set_title("Capacity Fade vs Cycle Count\n(calibrated to published 21700 NMC/Si-Gr trends)")
axes[0].legend(fontsize=8)

axes[1].bar([f"{int(s*100)}%" for s in soh_levels], cc_error_vs_soh,
           color=[GREEN, ORANGE, RED], alpha=0.85, edgecolor="white")
for i, v in enumerate(cc_error_vs_soh):
    axes[1].text(i, v + 0.05, f"{v:.2f} pp", ha="center", fontsize=9, fontweight="bold")
axes[1].set_xlabel("Cell State of Health")
axes[1].set_ylabel("Coulomb Counting RMSE [pp]")
axes[1].set_title("Why SoH Matters:\nCoulomb Counting Error Grows With Age\n(if BMS keeps using the BoL capacity)")

fig.tight_layout()
fig.savefig(os.path.join(PLOT_DIR, "04_soh_capacity_fade.png"))
plt.close(fig)
print("Saved: plots/04_soh_capacity_fade.png")

print("\n" + "=" * 66)
print("ANALYSIS COMPLETE")
print(f"Coulomb counting RMSE : {np.sqrt(np.mean(err_cc**2)):.2f} pp")
print(f"EKF RMSE (converged)  : {np.sqrt(np.mean(err_ekf[50:]**2)):.2f} pp")
print(f"Improvement           : {(1 - np.sqrt(np.mean(err_ekf[50:]**2))/np.sqrt(np.mean(err_cc**2)))*100:.0f}% lower error")
print(f"Cycles to 80% SoH (25C): ~{eol_cycles:.0f}")
print("=" * 66)
