"""
EV Traction Motor -- Torque-Speed Envelope, Efficiency Map, and Thermal Analysis

Models the operating envelope, loss behaviour, and winding thermal response of a
three phase interior permanent magnet synchronous motor (IPMSM), the dominant
traction motor topology in current EVs.

Motor parameters are grounded in a real, published teardown and test study of the
Tesla Model 3 (2018) rear drive unit motor (MotorXP-PM, "Performance Analysis of
the Tesla Model 3 Electric Motor using MotorXP-PM", June 2020), which measured the
stator and rotor geometry directly and validated peak torque and power against the
manufacturer's published ratings using finite element analysis. See the README for
full citation and a note on what is measured versus modelled here.

Author: Bapu Manu
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

np.random.seed(7)

# ---------------------------------------------------------------------------
# 1. MOTOR PARAMETERS (measured / published, Tesla Model 3 rear IPMSM)
# ---------------------------------------------------------------------------
POLE_PAIRS      = 3            # measured, MotorXP teardown
PHASE_R_20C     = 0.00475      # ohm, measured at 20degC
STACK_LENGTH_MM = 134.0        # mm
STATOR_OD_MM    = 225.0        # mm
STATOR_ID_MM    = 151.3        # mm

T_PEAK   = 430.0               # Nm, published + FEA validated peak torque
P_PEAK   = 192_000.0           # W, published + FEA validated peak power
I_PEAK   = 1000.0              # Arms phase current at the peak torque point
V_BUS_MIN = 231.0              # Vdc, minimum bus voltage to reach the peak point
BEMF_CONST_LL = 42.0           # V peak, line to line, per kRPM (measured, no load)

W_BASE_RPM = (P_PEAK / T_PEAK) * (60.0 / (2 * np.pi))
W_BASE = P_PEAK / T_PEAK        # rad/s

FIELD_WEAKENING_RATIO = 3.6
W_MAX = W_BASE * FIELD_WEAKENING_RATIO
W_MAX_RPM = W_BASE_RPM * FIELD_WEAKENING_RATIO

K_T = T_PEAK / I_PEAK           # Nm / Arms

T_WINDING_LIMIT_C = 155.0
T_COOLANT_C = 65.0

print("=" * 70)
print("EV TRACTION MOTOR -- IPMSM SIZING, EFFICIENCY, AND THERMAL ANALYSIS")
print("=" * 70)
print(f"\nMotor: Tesla Model 3 (2018) rear drive IPMSM (measured/published)")
print(f"  Pole pairs:            {POLE_PAIRS}")
print(f"  Phase resistance:      {PHASE_R_20C*1000:.3f} mOhm @ 20C")
print(f"  Peak torque:           {T_PEAK:.0f} Nm")
print(f"  Peak power:            {P_PEAK/1000:.0f} kW")
print(f"  Base speed:            {W_BASE_RPM:.0f} rpm")
print(f"  Max speed (assumed):   {W_MAX_RPM:.0f} rpm (field weakening ratio {FIELD_WEAKENING_RATIO}x)")
print(f"  Back EMF constant:     {BEMF_CONST_LL:.1f} Vpk,LL / kRPM")


# ---------------------------------------------------------------------------
# 2. TORQUE-SPEED ENVELOPE
# ---------------------------------------------------------------------------
def torque_envelope(w_rpm):
    w = np.asarray(w_rpm, dtype=float)
    t = np.where(w <= W_BASE_RPM, T_PEAK, P_PEAK / (w * 2 * np.pi / 60.0))
    t = np.where(w <= W_MAX_RPM, t, 0.0)
    return t


# ---------------------------------------------------------------------------
# 3. LOSS MODEL
# ---------------------------------------------------------------------------
def copper_loss(torque_nm, t_winding_c):
    i_phase = np.abs(torque_nm) / K_T
    r_temp = PHASE_R_20C * (1 + 0.00393 * (t_winding_c - 20.0))
    return 3.0 * i_phase**2 * r_temp


def iron_loss(w_rpm, torque_nm):
    w = np.asarray(w_rpm, dtype=float)
    flux_ratio = np.where(w <= W_BASE_RPM, 1.0, W_BASE_RPM / np.maximum(w, 1.0))
    speed_ratio = w / W_BASE_RPM
    P_FE_BASE = 900.0
    return P_FE_BASE * speed_ratio**1.5 * flux_ratio**2


def mechanical_loss(w_rpm):
    w = np.asarray(w_rpm, dtype=float)
    P_MECH_BASE = 250.0
    return P_MECH_BASE * (w / W_BASE_RPM)**2


def efficiency(w_rpm, torque_nm, t_winding_c=100.0):
    w_rad = w_rpm * 2 * np.pi / 60.0
    p_out = np.abs(torque_nm) * w_rad
    p_loss = (copper_loss(torque_nm, t_winding_c)
              + iron_loss(w_rpm, torque_nm)
              + mechanical_loss(w_rpm))
    p_in = p_out + p_loss
    with np.errstate(divide="ignore", invalid="ignore"):
        eff = np.where(p_in > 1.0, p_out / p_in, 0.0)
    return np.clip(eff, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 4. SYNTHETIC DRIVE CYCLE AND THERMAL RESPONSE
# ---------------------------------------------------------------------------
dt = 1.0
T_total = 1800.0
t = np.arange(0, T_total, dt)
n = len(t)

speed_rpm = np.zeros(n)
torque_demand = np.zeros(n)
i = 0
rng = np.random.default_rng(7)
while i < n:
    mode = rng.choice(["urban", "highway", "hard_accel", "idle"], p=[0.35, 0.30, 0.15, 0.20])
    if mode == "hard_accel":
        seg = min(int(rng.uniform(15, 25)), n - i)
    else:
        seg = min(150, n - i)
    tt = np.arange(seg)
    if mode == "urban":
        s = 2500 + 1500 * np.sin(2 * np.pi * tt / 90.0) ** 2
        trq = 120 + 60 * np.sin(2 * np.pi * tt / 60.0)
    elif mode == "highway":
        s = 6500 + 800 * np.sin(2 * np.pi * tt / 200.0)
        trq = torque_envelope(s) * 0.35
    elif mode == "hard_accel":
        s = np.linspace(1000, min(1000 + seg * 380, 9500), seg)
        trq = torque_envelope(s) * 0.92
    else:
        s = np.full(seg, 600.0)
        trq = np.full(seg, 5.0)
    speed_rpm[i:i + seg] = s
    torque_demand[i:i + seg] = np.minimum(trq, torque_envelope(s))
    i += seg

C_TH = 4200.0
R_TH = 0.028

FOLDBACK_START_C = T_WINDING_LIMIT_C * 0.90
FOLDBACK_BAND_C = T_WINDING_LIMIT_C - FOLDBACK_START_C

t_winding = np.zeros(n)
t_winding[0] = T_COOLANT_C + 15.0
torque_nm = np.zeros(n)
p_loss_series = np.zeros(n)
derate_events = 0
for k in range(1, n):
    margin = (T_WINDING_LIMIT_C - t_winding[k - 1]) / FOLDBACK_BAND_C
    derate = np.clip(margin, 0.15, 1.0) if t_winding[k - 1] > FOLDBACK_START_C else 1.0
    if derate < 1.0:
        derate_events += 1
    applied = torque_demand[k - 1] * derate
    torque_nm[k - 1] = applied

    p_cu = copper_loss(applied, t_winding[k - 1])
    p_fe = iron_loss(speed_rpm[k - 1], applied)
    p_mech = mechanical_loss(speed_rpm[k - 1])
    p_loss = p_cu + p_fe + p_mech
    p_loss_series[k - 1] = p_loss
    dT = (p_loss - (t_winding[k - 1] - T_COOLANT_C) / R_TH) / C_TH * dt
    t_winding[k] = t_winding[k - 1] + dT
torque_nm[-1] = torque_nm[-2]
p_loss_series[-1] = p_loss_series[-2]

t_peak = t_winding.max()
t_final = t_winding[-1]
time_to_90pct = None
target = T_COOLANT_C + 0.9 * (t_peak - T_COOLANT_C)
above = np.where(t_winding >= target)[0]
if len(above):
    time_to_90pct = t[above[0]]

print(f"\nDrive cycle thermal response ({T_total/60:.0f} min synthetic cycle):")
print(f"  Peak winding temperature:   {t_peak:.1f} C")
print(f"  Final winding temperature:  {t_final:.1f} C")
print(f"  Thermal limit (design):     {T_WINDING_LIMIT_C:.0f} C")
print(f"  Margin to limit at peak:    {T_WINDING_LIMIT_C - t_peak:.1f} C")
if time_to_90pct is not None:
    print(f"  Time to reach 90% of peak rise: {time_to_90pct/60:.1f} min")
print(f"  Time steps with thermal foldback active: {derate_events} of {n} "
      f"({derate_events/n*100:.1f}%)")


# ---------------------------------------------------------------------------
# 5. EFFICIENCY MAP
# ---------------------------------------------------------------------------
speed_grid = np.linspace(200, W_MAX_RPM, 160)
torque_grid = np.linspace(5, T_PEAK, 160)
SPEED_G, TORQUE_G = np.meshgrid(speed_grid, torque_grid)
ENV_G = torque_envelope(SPEED_G)
EFF_G = efficiency(SPEED_G, np.minimum(TORQUE_G, ENV_G), t_winding_c=100.0)
EFF_G = np.where(TORQUE_G <= ENV_G, EFF_G, np.nan)

peak_eff = np.nanmax(EFF_G)
peak_idx = np.unravel_index(np.nanargmax(EFF_G), EFF_G.shape)
peak_eff_speed = SPEED_G[peak_idx]
peak_eff_torque = TORQUE_G[peak_idx]

print(f"\nEfficiency map (100C winding assumption):")
print(f"  Peak efficiency: {peak_eff*100:.1f}% at {peak_eff_speed:.0f} rpm, {peak_eff_torque:.0f} Nm")
print(f"  Efficiency at peak torque, base speed: {efficiency(W_BASE_RPM, T_PEAK, 100.0)*100:.1f}%")
print(f"  Efficiency at cruise (highway block, ~35% torque, 6500 rpm): "
      f"{efficiency(6500, torque_envelope(6500)*0.35, 100.0)*100:.1f}%")


# ---------------------------------------------------------------------------
# 6. LOSS BREAKDOWN ACROSS SPEED AT RATED TORQUE
# ---------------------------------------------------------------------------
speed_sweep = np.linspace(200, W_MAX_RPM, 200)
torque_sweep = torque_envelope(speed_sweep)
cu_sweep = copper_loss(torque_sweep, 100.0)
fe_sweep = iron_loss(speed_sweep, torque_sweep)
mech_sweep = mechanical_loss(speed_sweep)


# ---------------------------------------------------------------------------
# 7. PLOTS
# ---------------------------------------------------------------------------
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})

fig, ax1 = plt.subplots(figsize=(11, 6.3))
w_plot = np.linspace(1, W_MAX_RPM, 400)
t_plot = torque_envelope(w_plot)
p_plot = t_plot * w_plot * 2 * np.pi / 60.0 / 1000.0

ax1.plot(w_plot, t_plot, color="#1A3A5C", lw=2.4, label="Torque limit")
ax1.axvline(W_BASE_RPM, color="#E8A020", ls="--", lw=1.4)
ax1.fill_between(w_plot[w_plot <= W_BASE_RPM], t_plot[w_plot <= W_BASE_RPM],
                  color="#1A3A5C", alpha=0.08)
ax1.fill_between(w_plot[w_plot > W_BASE_RPM], t_plot[w_plot > W_BASE_RPM],
                  color="#E8A020", alpha=0.10)
ax1.set_xlabel("Speed [rpm]")
ax1.set_ylabel("Torque [Nm]", color="#1A3A5C")
ax1.tick_params(axis="y", labelcolor="#1A3A5C")
ax1.set_ylim(0, T_PEAK * 1.12)
ax1.text(W_BASE_RPM / 2, T_PEAK * 1.04, "Constant torque\n(MTPA region)",
          ha="center", fontsize=9, color="#1A3A5C")
ax1.text((W_BASE_RPM + W_MAX_RPM) / 2, T_PEAK * 1.04, "Constant power\n(field weakening)",
          ha="center", fontsize=9, color="#B87400")

ax2 = ax1.twinx()
ax2.plot(w_plot, p_plot, color="#2E7D32", lw=2.0, ls="-.", label="Power")
ax2.set_ylabel("Power [kW]", color="#2E7D32")
ax2.tick_params(axis="y", labelcolor="#2E7D32")
ax2.set_ylim(0, P_PEAK / 1000 * 1.15)

ax1.set_title(f"IPMSM Torque-Speed Envelope  |  Base speed {W_BASE_RPM:.0f} rpm, "
              f"Peak {T_PEAK:.0f} Nm / {P_PEAK/1000:.0f} kW")
fig.tight_layout()
fig.savefig("plots/01_torque_speed_envelope.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(11, 6.6))
levels = np.arange(0.55, 0.99, 0.02)
cs = ax.contourf(SPEED_G, TORQUE_G, EFF_G, levels=levels, cmap="viridis", extend="both")
cbar = fig.colorbar(cs, ax=ax, label="Efficiency")
ax.plot(w_plot, t_plot, color="white", lw=2.2)
ax.plot(peak_eff_speed, peak_eff_torque, "r*", markersize=16,
        label=f"Peak efficiency {peak_eff*100:.1f}%")
ax.set_xlabel("Speed [rpm]")
ax.set_ylabel("Torque [Nm]")
ax.set_title("Efficiency Map (100C winding) with Torque-Speed Envelope Overlaid")
ax.legend(loc="lower right")
ax.set_ylim(0, T_PEAK * 1.05)
fig.tight_layout()
fig.savefig("plots/02_efficiency_map.png", dpi=150)
plt.close(fig)

fig = plt.figure(figsize=(11, 8.5))
gs = gridspec.GridSpec(3, 1, height_ratios=[1, 1, 1.2], hspace=0.35)

ax0 = fig.add_subplot(gs[0])
ax0.plot(t / 60.0, speed_rpm, color="#1A3A5C", lw=1.1)
ax0.set_ylabel("Speed [rpm]")
ax0.set_title("Synthetic 30 Minute Drive Cycle and Winding Thermal Response")

ax1b = fig.add_subplot(gs[1], sharex=ax0)
ax1b.plot(t / 60.0, torque_nm, color="#5E3A8C", lw=1.1)
ax1b.set_ylabel("Torque [Nm]")

ax2b = fig.add_subplot(gs[2], sharex=ax0)
ax2b.plot(t / 60.0, t_winding, color="#C62828", lw=1.8, label="Winding temperature")
ax2b.axhline(T_WINDING_LIMIT_C, color="#C62828", ls="--", lw=1.2,
             label=f"Design limit ({T_WINDING_LIMIT_C:.0f} C)")
ax2b.axhline(T_COOLANT_C, color="#2E7D32", ls=":", lw=1.2, label=f"Coolant ({T_COOLANT_C:.0f} C)")
ax2b.set_ylabel("Winding Temp [C]")
ax2b.set_xlabel("Time [min]")
ax2b.legend(loc="lower right", fontsize=8.5)
ax2b.set_ylim(T_COOLANT_C - 5, T_WINDING_LIMIT_C + 20)

fig.savefig("plots/03_drive_cycle_thermal.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(11, 6.3))
ax.stackplot(speed_sweep, cu_sweep, fe_sweep, mech_sweep,
             labels=["Copper loss (I2R)", "Iron loss", "Mechanical loss"],
             colors=["#C62828", "#E8A020", "#5E3A8C"], alpha=0.85)
ax.axvline(W_BASE_RPM, color="black", ls="--", lw=1.0, alpha=0.6)
ax.text(W_BASE_RPM * 1.02, ax.get_ylim()[1] * 0.92, "base speed", fontsize=8.5)
ax.set_xlabel("Speed [rpm]")
ax.set_ylabel("Loss [W]")
ax.set_title("Loss Breakdown Along the Torque-Speed Envelope (100C winding)")
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig("plots/04_loss_breakdown.png", dpi=150)
plt.close(fig)

print("\nSaved 4 plots to plots/")
print("=" * 70)
