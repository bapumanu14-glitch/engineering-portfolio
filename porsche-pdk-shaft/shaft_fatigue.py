"""
Porsche 992 PDK Input Shaft — Fatigue Analysis
Author: Bapu Manu | SRH Berlin University of Applied Sciences
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import os

# ── Output directory ───────────────────────────────────────────────────────
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOT_DIR = os.path.join(OUT_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.3,
    "figure.dpi": 150,
})

# ══════════════════════════════════════════════════════════════════════════════
# 1. ENGINE & GEARBOX PARAMETERS — Porsche 992 Carrera S (8-speed PDK)
# ══════════════════════════════════════════════════════════════════════════════
T_engine_nom  = 450.0    # Nm — rated torque
T_engine_peak = 530.0    # Nm — overboost peak torque
n_engine_peak = 6500.0   # rpm — peak torque speed
n_engine_max  = 7500.0   # rpm — redline

# 8-speed PDK gear ratios (Porsche ZF 8HP based)
gear_ratios = {1: 4.095, 2: 2.470, 3: 1.674, 4: 1.219,
               5: 0.943, 6: 0.758, 7: 0.624, 8: 0.512}
final_drive = 3.444

print("=" * 60)
print("PORSCHE 992 PDK INPUT SHAFT — FATIGUE ANALYSIS")
print("=" * 60)
print(f"\nEngine: 3.0L twin-turbo flat-6")
print(f"  Nominal torque : {T_engine_nom} Nm at {n_engine_peak} rpm")
print(f"  Peak torque    : {T_engine_peak} Nm (overboost)")
print(f"  Redline        : {n_engine_max} rpm")

# ══════════════════════════════════════════════════════════════════════════════
# 2. SHAFT GEOMETRY
# ══════════════════════════════════════════════════════════════════════════════
# Stepped shaft: engine → bearing A → gear mesh → bearing B → clutch drum
#
#   |<-- 30mm -->|<-- 80mm -->|<-- 60mm -->|<-- 30mm -->|
#   [  d=28mm   ][   d=35mm  ][   d=32mm  ][   d=28mm  ]
#   [  Bearing A ][  Main    ][  Spline   ][  Bearing B ]
#
# All forces act at the gear mesh centre (x = 110mm from bearing A)

D_main    = 0.035   # m  — main section diameter (35 mm)
D_bearing = 0.028   # m  — bearing journal diameter (28 mm)
D_spline  = 0.032   # m  — spline section diameter (32 mm)

# Shaft station x-coordinates (m from bearing A)
x_A    = 0.000   # Bearing A (left)
x_gear = 0.110   # Gear mesh point
x_B    = 0.200   # Bearing B (right)
L      = x_B     # Total span

# Pitch circle radius of input gear (1st gear pinion on PDK input shaft)
# Estimate: module m=3, z=18 teeth → r = m*z/2 = 3*18/2 = 27 mm
r_gear = 0.027   # m

# Helix angle (helical gears in PDK)
psi = np.radians(25)   # 25° helix angle

print(f"\nShaft geometry:")
print(f"  Main diameter  : {D_main*1000:.0f} mm")
print(f"  Bearing journal: {D_bearing*1000:.0f} mm")
print(f"  Span A–B       : {L*1000:.0f} mm")
print(f"  Gear mesh at   : x = {x_gear*1000:.0f} mm from A")

# ══════════════════════════════════════════════════════════════════════════════
# 3. GEAR MESH FORCES
# ══════════════════════════════════════════════════════════════════════════════
# Using peak torque (design case)
T = T_engine_peak   # Nm

# Tangential force at gear pitch circle
W_t = T / r_gear
# Radial force (pressure angle 20°)
phi = np.radians(20)
W_r = W_t * np.tan(phi) / np.cos(psi)
# Axial force (from helix)
W_a = W_t * np.tan(psi)

print(f"\nGear mesh forces (T = {T} Nm, r = {r_gear*1000:.0f} mm):")
print(f"  Tangential W_t : {W_t:.1f} N")
print(f"  Radial     W_r : {W_r:.1f} N")
print(f"  Axial      W_a : {W_a:.1f} N")

# ══════════════════════════════════════════════════════════════════════════════
# 4. BEARING REACTIONS & BENDING MOMENT DIAGRAM
# ══════════════════════════════════════════════════════════════════════════════
# Simply supported beam A–B, load at x_gear
a = x_gear
b = L - x_gear

# Vertical plane (radial force W_r)
R_Av = W_r * b / L
R_Bv = W_r * a / L

# Horizontal plane (tangential force W_t)
R_Ah = W_t * b / L
R_Bh = W_t * a / L

# Bending moments at gear mesh location
Mv = R_Av * a    # Vertical plane moment
Mh = R_Ah * a    # Horizontal plane moment
M_total = np.sqrt(Mv**2 + Mh**2)  # Resultant bending moment

print(f"\nBearing reactions:")
print(f"  R_Av = {R_Av:.1f} N  |  R_Bv = {R_Bv:.1f} N  (vertical)")
print(f"  R_Ah = {R_Ah:.1f} N  |  R_Bh = {R_Bh:.1f} N  (horizontal)")
print(f"\nBending moments at gear mesh (x = {x_gear*1000:.0f} mm):")
print(f"  M_vertical   : {Mv:.2f} Nm")
print(f"  M_horizontal : {Mh:.2f} Nm")
print(f"  M_resultant  : {M_total:.2f} Nm")

# BMD arrays for plotting
x_pts = np.array([0, x_gear, L])
Mv_pts = np.array([0, Mv, 0])
Mh_pts = np.array([0, Mh, 0])
M_res_pts = np.sqrt(Mv_pts**2 + Mh_pts**2)

# ══════════════════════════════════════════════════════════════════════════════
# 5. STRESS CALCULATION AT CRITICAL SECTION (gear mesh, main diameter)
# ══════════════════════════════════════════════════════════════════════════════
d = D_main
r_shaft = d / 2

# Section moduli
I   = np.pi * d**4 / 64      # m⁴
Z   = I / r_shaft             # m³ — bending
J   = np.pi * d**4 / 32      # m⁴
Zp  = J / r_shaft             # m³ — torsion

# Nominal stresses (Pa → MPa)
sigma_b_nom = M_total / Z / 1e6    # MPa — bending
tau_nom     = T / Zp / 1e6         # MPa — torsion

print(f"\nNominal stresses at critical section (d = {d*1000:.0f} mm):")
print(f"  Bending stress σ_b : {sigma_b_nom:.2f} MPa")
print(f"  Torsional stress τ : {tau_nom:.2f} MPa")

# Stress concentration factors (shoulder fillet, r/d ≈ 0.05)
Kf_b = 1.8    # fatigue stress concentration — bending
Kf_t = 1.4    # fatigue stress concentration — torsion

# Actual fatigue stresses
sigma_a = Kf_b * sigma_b_nom    # alternating (fully reversed bending)
sigma_m = 0.0                   # mean bending (rotating shaft = 0)
tau_m   = Kf_t * tau_nom        # mean torsion (steady torque)

# Von Mises equivalent stresses
sigma_a_vm = np.sqrt(sigma_a**2 + 3 * (0.0)**2)    # alternating
sigma_m_vm = np.sqrt(sigma_m**2 + 3 * tau_m**2)    # mean

print(f"\nFatigue stresses (with Kf_b={Kf_b}, Kf_t={Kf_t}):")
print(f"  σ_a (alternating) : {sigma_a:.2f} MPa")
print(f"  τ_m (mean)        : {tau_m:.2f} MPa")
print(f"  σ_a (von Mises)   : {sigma_a_vm:.2f} MPa")
print(f"  σ_m (von Mises)   : {sigma_m_vm:.2f} MPa")

# ══════════════════════════════════════════════════════════════════════════════
# 6. MATERIAL PROPERTIES — 20MnCr5 (case-hardened, standard gearbox steel)
# ══════════════════════════════════════════════════════════════════════════════
Su  = 1200.0   # MPa — ultimate tensile strength
Sy  = 1000.0   # MPa — yield strength
Se_prime = 0.504 * Su   # MPa — base endurance limit (steel, Su < 1400 MPa)

print(f"\nMaterial: 20MnCr5 (case-hardened)")
print(f"  σ_UTS            : {Su:.0f} MPa")
print(f"  σ_y              : {Sy:.0f} MPa")
print(f"  σ_e' (base)      : {Se_prime:.1f} MPa")

# ══════════════════════════════════════════════════════════════════════════════
# 7. MARIN FACTORS — Modified Endurance Limit
# ══════════════════════════════════════════════════════════════════════════════
# Surface finish (ground finish for gearbox shafts)
ka = 1.58 * (Su**-0.085)      # Marin surface factor (ground)

# Size factor (d = 35 mm)
d_mm = d * 1000
if 8 <= d_mm <= 51:
    kb = 1.24 * d_mm**(-0.107)
else:
    kb = 1.51 * d_mm**(-0.157)

# Load factor (bending)
kc = 1.0

# Temperature factor (< 150°C)
kd = 1.0

# Reliability factor (99% reliability)
ke = 0.814

# Miscellaneous (no additional factors)
kf = 1.0

Se = ka * kb * kc * kd * ke * kf * Se_prime

print(f"\nMarin factors:")
print(f"  ka (surface)     : {ka:.3f}")
print(f"  kb (size)        : {kb:.3f}")
print(f"  kc (load)        : {kc:.3f}")
print(f"  kd (temperature) : {kd:.3f}")
print(f"  ke (reliability) : {ke:.3f}")
print(f"  Se (modified)    : {Se:.1f} MPa")

# ══════════════════════════════════════════════════════════════════════════════
# 8. FATIGUE CRITERIA — Modified Goodman
# ══════════════════════════════════════════════════════════════════════════════
# Goodman: σ_a/Se + σ_m/Su = 1/n
# Solving for safety factor n:
n_goodman = 1.0 / (sigma_a_vm / Se + sigma_m_vm / Su)

# Langer yield check
n_yield = Sy / (sigma_a_vm + sigma_m_vm)

print(f"\nFatigue analysis (Modified Goodman):")
print(f"  σ_a / Se         : {sigma_a_vm/Se:.4f}")
print(f"  σ_m / Su         : {sigma_m_vm/Su:.4f}")
print(f"  Safety factor n  : {n_goodman:.2f}")
print(f"  Yield FoS        : {n_yield:.2f}")

if n_goodman >= 1.5:
    status = "PASS (FoS ≥ 1.5)"
elif n_goodman >= 1.0:
    status = "MARGINAL (1.0 ≤ FoS < 1.5)"
else:
    status = "FAIL (FoS < 1.0)"
print(f"  Status           : {status}")

# ══════════════════════════════════════════════════════════════════════════════
# 9. S-N CURVE & FATIGUE LIFE
# ══════════════════════════════════════════════════════════════════════════════
# Two-point S-N (Shigley approach)
f = 0.9   # fraction of Su at 10³ cycles
N_e = 1e6  # endurance limit cycle count

# S-N curve parameters
a_sn = (f * Su)**2 / Se
b_sn = -(1/3) * np.log10(f * Su / Se)

# Life at current alternating stress
if sigma_a_vm < Se:
    N_life = float('inf')
    life_str = "Infinite life (below endurance limit)"
else:
    N_life = (sigma_a_vm / a_sn)**(1 / b_sn)
    if N_life > 1e9:
        life_str = f">10⁹ cycles"
    else:
        life_str = f"{N_life:.2e} cycles"

print(f"\nS-N curve (Shigley two-point method):")
print(f"  a = {a_sn:.2f}, b = {b_sn:.4f}")
print(f"  Operating σ_a    : {sigma_a_vm:.2f} MPa")
print(f"  Endurance limit  : {Se:.1f} MPa")
print(f"  Fatigue life     : {life_str}")

# ══════════════════════════════════════════════════════════════════════════════
# 10. STRESS ALONG SHAFT LENGTH
# ══════════════════════════════════════════════════════════════════════════════
x_fine = np.linspace(0, L, 500)
M_fine = np.where(x_fine <= x_gear,
                  R_Av * x_fine,
                  R_Av * x_fine - W_r * (x_fine - x_gear))
Mh_fine = np.where(x_fine <= x_gear,
                   R_Ah * x_fine,
                   R_Ah * x_fine - W_t * (x_fine - x_gear))
M_res_fine = np.sqrt(M_fine**2 + Mh_fine**2)

# Diameter along shaft
D_fine = np.where(x_fine < 0.03, D_bearing,
         np.where(x_fine < 0.11, D_main,
         np.where(x_fine < 0.17, D_spline, D_bearing)))

Z_fine = np.pi * D_fine**3 / 32
sigma_b_fine = (M_res_fine / Z_fine) / 1e6   # MPa

# ══════════════════════════════════════════════════════════════════════════════
# 11. PLOTS
# ══════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(14, 10))
fig.suptitle("Porsche 992 PDK Input Shaft — Fatigue Analysis",
             fontsize=13, fontweight='bold', y=0.98)
gs = GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

RED    = "#C20E1A"
NAVY   = "#1A1A2E"
TEAL   = "#2E86AB"
ORANGE = "#E07A5F"
GREEN  = "#3D9970"

# ── Plot 1: Bending Moment Diagram ─────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax1.fill_between([0, x_gear*1000, L*1000],
                 [0, M_total, 0], alpha=0.25, color=TEAL)
ax1.plot([0, x_gear*1000, L*1000],
         [0, Mv, 0], '--', color=TEAL, lw=1.5, label='Vertical plane')
ax1.plot([0, x_gear*1000, L*1000],
         [0, Mh, 0], '--', color=ORANGE, lw=1.5, label='Horizontal plane')
ax1.plot([0, x_gear*1000, L*1000],
         [0, M_total, 0], color=NAVY, lw=2, label='Resultant')
ax1.axvline(x_gear*1000, color='grey', lw=0.8, ls=':')
ax1.annotate(f'{M_total:.1f} Nm', xy=(x_gear*1000, M_total),
             xytext=(x_gear*1000+8, M_total*0.85),
             fontsize=8, color=NAVY,
             arrowprops=dict(arrowstyle='->', color=NAVY, lw=0.8))
ax1.set_xlabel('x (mm)')
ax1.set_ylabel('Bending Moment (Nm)')
ax1.set_title('Bending Moment Diagram')
ax1.legend(fontsize=7)

# ── Plot 2: Bending Stress Along Shaft ─────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax2.plot(x_fine*1000, sigma_b_fine, color=RED, lw=2)
ax2.axhline(Se, color=GREEN, lw=1.5, ls='--', label=f'Se = {Se:.0f} MPa')
ax2.fill_between(x_fine*1000, sigma_b_fine, Se,
                 where=sigma_b_fine > Se, alpha=0.2, color=RED,
                 label='Above endurance limit')
ax2.axvline(x_gear*1000, color='grey', lw=0.8, ls=':')
ax2.set_xlabel('x (mm)')
ax2.set_ylabel('Bending Stress (MPa)')
ax2.set_title('Nominal Bending Stress\nAlong Shaft')
ax2.legend(fontsize=7)

# ── Plot 3: S-N Curve ───────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
N_range = np.logspace(3, 9, 500)
# S-N: S = a * N^b for N < 1e6, S = Se for N >= 1e6
S_range = np.where(N_range <= N_e,
                   a_sn * N_range**b_sn,
                   Se * np.ones_like(N_range))
ax3.loglog(N_range, S_range, color=NAVY, lw=2, label='S-N curve (20MnCr5)')
ax3.axhline(Se, color=GREEN, lw=1.2, ls='--', label=f'Se = {Se:.0f} MPa')
ax3.scatter([N_life if N_life != float('inf') else 1e9],
            [sigma_a_vm], color=RED, s=80, zorder=5,
            label=f'Operating point\nσ_a = {sigma_a_vm:.0f} MPa')
ax3.axhline(sigma_a_vm, color=RED, lw=0.8, ls=':')
ax3.set_xlabel('Cycles N')
ax3.set_ylabel('Stress Amplitude (MPa)')
ax3.set_title('S-N Curve')
ax3.legend(fontsize=7)
ax3.set_ylim(100, Su * 1.1)

# ── Plot 4: Modified Goodman Diagram ───────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0])
sm_line = np.linspace(0, Su, 300)
sa_goodman = Se * (1 - sm_line / Su)
sa_langer  = Sy - sm_line
sa_langer  = np.clip(sa_langer, 0, None)

ax4.plot(sm_line, sa_goodman, color=NAVY, lw=2, label='Goodman line')
ax4.plot(sm_line, sa_langer,  color=ORANGE, lw=1.5, ls='--', label='Langer (yield)')
ax4.fill_between(sm_line, 0, np.minimum(sa_goodman, sa_langer),
                 alpha=0.1, color=GREEN, label='Safe zone')
ax4.scatter([sigma_m_vm], [sigma_a_vm], color=RED, s=100, zorder=5,
            label=f'Operating point\n(n={n_goodman:.2f})')
# Load line
ax4.plot([0, sigma_m_vm * 1.4], [0, sigma_a_vm * 1.4],
         color=RED, lw=0.8, ls=':', alpha=0.6)
ax4.set_xlabel('Mean Stress σ_m (MPa)')
ax4.set_ylabel('Alternating Stress σ_a (MPa)')
ax4.set_title('Modified Goodman Diagram')
ax4.legend(fontsize=7)
ax4.set_xlim(0, Su)
ax4.set_ylim(0, Se * 1.3)

# ── Plot 5: Summary Table ───────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 1])
ax5.axis('off')
table_data = [
    ['Parameter', 'Value', 'Unit'],
    ['Engine torque (peak)', f'{T:.0f}', 'Nm'],
    ['Shaft diameter (main)', f'{D_main*1000:.0f}', 'mm'],
    ['Bending moment', f'{M_total:.1f}', 'Nm'],
    ['σ_a (alternating)', f'{sigma_a_vm:.1f}', 'MPa'],
    ['σ_m (mean)', f'{sigma_m_vm:.1f}', 'MPa'],
    ['Se (modified)', f'{Se:.1f}', 'MPa'],
    ['Safety factor n', f'{n_goodman:.2f}', '—'],
    ['Yield FoS', f'{n_yield:.2f}', '—'],
    ['Fatigue life', life_str[:20], ''],
    ['Status', status[:18], ''],
]
col_colors = [[NAVY, NAVY, NAVY]] + [['#EDF2F7', 'white', '#EDF2F7']] * (len(table_data)-1)
cell_colors = col_colors
tbl = ax5.table(cellText=table_data[1:], colLabels=table_data[0],
                cellLoc='center', loc='center',
                colWidths=[0.55, 0.25, 0.2])
tbl.auto_set_font_size(False)
tbl.set_fontsize(8)
for (row, col), cell in tbl.get_celld().items():
    if row == 0:
        cell.set_facecolor(NAVY)
        cell.set_text_props(color='white', fontweight='bold')
    elif row % 2 == 0:
        cell.set_facecolor('#EDF2F7')
    cell.set_edgecolor('#CCCCCC')
    cell.set_linewidth(0.5)
ax5.set_title('Results Summary', fontweight='bold', fontsize=10)

# ── Plot 6: Gear Forces Breakdown ──────────────────────────────────────────
ax6 = fig.add_subplot(gs[1, 2])
forces = [W_t, W_r, W_a, np.sqrt(W_t**2 + W_r**2 + W_a**2)]
labels = ['Tangential\nW_t', 'Radial\nW_r', 'Axial\nW_a', 'Resultant']
colors = [TEAL, ORANGE, GREEN, RED]
bars = ax6.bar(labels, forces, color=colors, alpha=0.85, edgecolor='white', lw=0.5)
for bar, val in zip(bars, forces):
    ax6.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 150,
             f'{val:.0f} N', ha='center', va='bottom', fontsize=8, fontweight='bold')
ax6.set_ylabel('Force (N)')
ax6.set_title('Gear Mesh Forces\n(1st gear, peak torque)')
ax6.set_ylim(0, max(forces) * 1.2)

plt.savefig(os.path.join(PLOT_DIR, "shaft_fatigue_analysis.png"),
            bbox_inches='tight', dpi=150)
plt.close()
print(f"\nPlot saved to: plots/shaft_fatigue_analysis.png")

# ══════════════════════════════════════════════════════════════════════════════
# 12. GEAR-BY-GEAR SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GEAR-BY-GEAR LOAD SUMMARY")
print("=" * 60)
print(f"{'Gear':>5} {'Ratio':>7} {'T_out (Nm)':>12} {'W_t (N)':>10} {'M_b (Nm)':>10} {'n_Goodman':>11}")
print("-" * 60)

gear_results = []
for g, ratio in gear_ratios.items():
    T_out = T_engine_nom * ratio
    Wt = T_engine_nom / r_gear
    Wr = Wt * np.tan(phi) / np.cos(psi)
    RAv = Wr * (L - x_gear) / L
    RAh = Wt * (L - x_gear) / L
    Mv_g = RAv * x_gear
    Mh_g = RAh * x_gear
    Mt = np.sqrt(Mv_g**2 + Mh_g**2)
    Z_main = np.pi * D_main**3 / 32
    sigma_b_g = Kf_b * (Mt / Z_main) / 1e6
    tau_g = Kf_t * (T_engine_nom / Zp) / 1e6
    sa_g = sigma_b_g
    sm_g = np.sqrt(3) * tau_g
    n_g = 1.0 / (sa_g / Se + sm_g / Su)
    gear_results.append((g, ratio, T_out, Wt, Mt, n_g))
    print(f"{g:>5} {ratio:>7.3f} {T_out:>12.1f} {Wt:>10.1f} {Mt:>10.2f} {n_g:>11.2f}")

print("-" * 60)
print(f"\nCritical gear: 1st (highest torque multiplication, highest output shaft load)")
print(f"Input shaft sees same torque in all gears — analysis above is for input shaft.")

# Gear comparison plot
fig2, axes = plt.subplots(1, 2, figsize=(11, 4))
fig2.suptitle("Gear-by-Gear Analysis — Porsche 992 PDK",
              fontsize=12, fontweight='bold')

gears = [r[0] for r in gear_results]
T_outs = [r[2] for r in gear_results]
n_fos = [r[5] for r in gear_results]

axes[0].bar(gears, T_outs, color=TEAL, alpha=0.85, edgecolor='white')
axes[0].set_xlabel('Gear')
axes[0].set_ylabel('Output Shaft Torque (Nm)')
axes[0].set_title('Output Torque by Gear\n(Input shaft T = constant)')
for i, (g, t) in enumerate(zip(gears, T_outs)):
    axes[0].text(g, t + 50, f'{t:.0f}', ha='center', fontsize=8)

bar_colors = [RED if n < 1.5 else (ORANGE if n < 2.0 else GREEN) for n in n_fos]
axes[1].bar(gears, n_fos, color=bar_colors, alpha=0.85, edgecolor='white')
axes[1].axhline(1.5, color=RED, ls='--', lw=1.5, label='Target FoS = 1.5')
axes[1].set_xlabel('Gear')
axes[1].set_ylabel('Goodman Safety Factor')
axes[1].set_title('Safety Factor by Gear\n(Input shaft, nominal torque)')
axes[1].legend(fontsize=8)
for i, (g, n) in enumerate(zip(gears, n_fos)):
    axes[1].text(g, n + 0.03, f'{n:.2f}', ha='center', fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(PLOT_DIR, "gear_comparison.png"),
            bbox_inches='tight', dpi=150)
plt.close()
print(f"Plot saved to: plots/gear_comparison.png")

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print(f"Results: Goodman FoS = {n_goodman:.2f} | Yield FoS = {n_yield:.2f}")
print(f"Status : {status}")
print("=" * 60)
