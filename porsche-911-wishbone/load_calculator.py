"""
load_calculator.py
------------------
Phase 1: Vehicle Dynamics Load Cases for
Porsche 911 (992) Front Upper Wishbone

Calculates the forces acting on the front upper wishbone under:
  - Static (parked)
  - Hard cornering  (1.5g lateral — design load)
  - Emergency braking (1.5g longitudinal)
  - Combined worst case (1.2g lateral + 1.2g braking)

These outputs are the boundary conditions for Phase 3 FEA.

Author : Bapu Manu | HAW Hamburg | July 2026
Reference: Porsche 911 992 GT3 technical specifications
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 1. VEHICLE PARAMETERS — Porsche 911 (992 GT3 base)
# ─────────────────────────────────────────────────────────────────────────────
g  = 9.81          # m/s²  gravitational acceleration

# Mass & weight distribution
m_total  = 1418.0  # kg   kerb weight (992 GT3, DIN)
wb_front = 0.385   # –    front axle weight fraction (rear-engine: 38.5% front)
m_front  = m_total * wb_front          # kg  front axle mass
m_wheel  = m_front / 2                # kg  per front wheel (static)
W_total  = m_total * g                 # N   total vehicle weight
W_wheel  = m_wheel * g                 # N   static front wheel load

# Geometry (mm → m)
track_f   = 1.543       # m   front track width (centre-to-centre of tyres)
wheelbase = 2.456       # m
cg_height = 0.440       # m   estimated CG height
tyre_r    = 0.330       # m   loaded tyre radius (front 255/35 ZR20)
half_t    = track_f / 2 # m   half track

# Suspension geometry — front double wishbone
h_uw      = 0.360       # m   upper wishbone ball-joint height from ground
h_lw      = 0.140       # m   lower wishbone ball-joint height from ground
l_uw      = 0.280       # m   upper wishbone arm length (pivot to ball joint)
l_lw      = 0.355       # m   lower wishbone arm length
h_wc      = tyre_r      # m   wheel centre height ≈ tyre radius

# Material — Al 6061-T6 (Phase 3 material input)
E_al     = 68.9e9       # Pa   Young's modulus
sigma_y  = 276e6        # Pa   Yield strength
sigma_u  = 310e6        # Pa   Ultimate tensile strength
FOS_target = 2.5        # –    Minimum factor of safety

# ─────────────────────────────────────────────────────────────────────────────
# 2. HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def outer_wheel_load(ay_g, ax_g=0.0):
    """
    Calculate outer front wheel load under combined cornering + braking.

    ay_g : lateral acceleration in g (positive = turning left → outer = right)
    ax_g : longitudinal deceleration in g (positive = braking)

    Weight transfer model (simplified lateral):
      ΔFz_lateral  = m_total * ay * cg_height / track_f
      ΔFz_braking  = m_total * ax * cg_height / wheelbase * wb_front  (front bias ~70%)
    """
    ay   = ay_g * g
    ax   = ax_g * g

    # Lateral weight transfer (both axles share this)
    delta_lat  = m_total * ay  * cg_height / track_f

    # Longitudinal weight transfer to front
    delta_long = m_total * ax  * cg_height / wheelbase * 0.70  # 70% braking front

    Fz_outer = W_wheel + delta_lat / 2 + delta_long / 2
    Fy_outer = m_total * ay / 2          # lateral tyre force at outer wheel
    Fx_outer = m_total * ax / 2 * 0.70  # braking force (front bias)

    return Fz_outer, Fy_outer, Fx_outer


def wishbone_forces(Fz, Fy, Fx):
    """
    Resolve wheel contact forces into upper and lower wishbone member forces.

    Model: 2D statics of the upright (treated as rigid body).
    Ball joints = pin joints.

    Force equilibrium at the upright:
      ΣFx = 0 → F_uw_x + F_lw_x = Fy   (lateral balance)
      ΣFy = 0 → F_uw_z + F_lw_z = Fz   (vertical balance)
      ΣM_lw = 0 → moments about lower wishbone joint

    Simplification: wishbones assumed horizontal for initial sizing.
    (Full 3D solution requires CAD geometry — done in Phase 3.)
    """
    arm_ratio = (h_wc - h_lw) / (h_uw - h_lw)   # UW share of Fz
    F_uw_z    =  arm_ratio * Fz + (1 - arm_ratio) * Fy  * (h_wc - h_lw) / (h_uw - h_lw)
    F_uw_total = np.sqrt(F_uw_z**2 + (Fy / 2)**2 + (Fx / 2)**2)

    F_lw_z    = Fz - F_uw_z
    F_lw_total = np.sqrt(F_lw_z**2 + (Fy / 2)**2 + (Fx / 2)**2)

    return F_uw_total, F_lw_total


# ─────────────────────────────────────────────────────────────────────────────
# 3. LOAD CASES
# ─────────────────────────────────────────────────────────────────────────────

cases = {
    'Static':           (0.0,  0.0),
    'Hard cornering\n1.5g lateral':   (1.5,  0.0),
    'Emergency braking\n1.5g':        (0.0,  1.5),
    'Combined\n1.2g + 1.2g': (1.2,  1.2),
}

print('=' * 62)
print('  PORSCHE 911 (992 GT3) FRONT UPPER WISHBONE — LOAD CASES')
print('=' * 62)
print(f'  Vehicle mass     : {m_total:.0f} kg')
print(f'  Front axle share : {wb_front*100:.1f}%  ({m_front:.0f} kg  →  {W_wheel:.0f} N/wheel static)')
print(f'  Front track      : {track_f*1000:.0f} mm')
print(f'  CG height        : {cg_height*1000:.0f} mm')
print(f'  UW geometry      : h={h_uw*1000:.0f} mm, L={l_uw*1000:.0f} mm')
print(f'  Material         : Al 6061-T6  (σy={sigma_y/1e6:.0f} MPa)')
print(f'  Target FoS       : {FOS_target}')
print('=' * 62 + '\n')

results = {}
for name, (ay, ax) in cases.items():
    Fz, Fy, Fx = outer_wheel_load(ay, ax)
    F_uw, F_lw  = wishbone_forces(Fz, Fy, Fx)
    results[name] = dict(ay=ay, ax=ax, Fz=Fz, Fy=Fy, Fx=Fx, F_uw=F_uw, F_lw=F_lw)

    label = name.replace('\n', ' ')
    print(f'  CASE: {label}')
    print(f'    Wheel loads  → Fz={Fz:7.0f} N  |  Fy={Fy:6.0f} N  |  Fx={Fx:6.0f} N')
    print(f'    Upper wishbone force : {F_uw:7.0f} N  ({F_uw/1000:.2f} kN)')
    print(f'    Lower wishbone force : {F_lw:7.0f} N  ({F_lw/1000:.2f} kN)')

    # Allowable cross-section for FoS = 2.5 (pure axial, solid circular rod)
    A_req   = F_uw * FOS_target / sigma_y          # m²
    d_req   = np.sqrt(4 * A_req / np.pi) * 1000   # mm
    print(f'    Min. rod diameter    : {d_req:.1f} mm  (solid Al, FoS {FOS_target}, pure axial)')
    print()

# Critical case for FEA
critical = max(results, key=lambda k: results[k]['F_uw'])
crit = results[critical]
print('─' * 62)
print(f'  CRITICAL CASE FOR FEA : {critical.replace(chr(10)," ")}')
print(f'  Upper wishbone load   : {crit["F_uw"]:.0f} N  ({crit["F_uw"]/1000:.2f} kN)')
print(f'  Apply in ANSYS as:')
print(f'    Fz (vertical)  = {crit["Fz"]:.0f} N  ↑  at outboard ball joint')
print(f'    Fy (lateral)   = {crit["Fy"]:.0f} N  →  at outboard ball joint')
print(f'    Fx (braking)   = {crit["Fx"]:.0f} N  →  at outboard ball joint')
print('─' * 62 + '\n')


# ─────────────────────────────────────────────────────────────────────────────
# 4. PLOTS
# ─────────────────────────────────────────────────────────────────────────────

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 9.5,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'grid.alpha': 0.3, 'figure.dpi': 150,
    'savefig.dpi': 200, 'savefig.bbox': 'tight',
})
BLUE = '#1B3A6B'; ORANGE = '#E07B39'; RED = '#C0392B'; GREEN = '#2E8B57'

Path('plots').mkdir(exist_ok=True)

# Plot 1: Load case comparison bar chart
fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
labels = [k.replace('\n', '\n') for k in results]
colors = [BLUE, ORANGE, RED, '#7D3C98']

for ax_i, (key, ylabel) in enumerate(zip(['Fz', 'F_uw', 'F_lw'],
                                          ['Vertical Wheel Load Fz [N]',
                                           'Upper Wishbone Force [N]',
                                           'Lower Wishbone Force [N]'])):
    vals = [results[k][key] for k in results]
    bars = axes[ax_i].bar(range(len(labels)), vals, color=colors, width=0.6, edgecolor='white')
    axes[ax_i].set_xticks(range(len(labels)))
    axes[ax_i].set_xticklabels(labels, fontsize=8)
    axes[ax_i].set_ylabel(ylabel)
    axes[ax_i].set_title(ylabel.split('[')[0].strip())
    for bar, val in zip(bars, vals):
        axes[ax_i].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50,
                        f'{val:.0f}', ha='center', va='bottom', fontsize=7.5, fontweight='bold')

fig.suptitle('Porsche 911 (992) Front Suspension — Load Case Comparison', fontsize=11, fontweight='bold')
fig.tight_layout()
fig.savefig('plots/01_load_cases.png')
plt.close(fig)
print('Saved: plots/01_load_cases.png')

# Plot 2: Weight transfer visualisation
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

ay_range = np.linspace(0, 2.0, 100)
Fz_outer = [(outer_wheel_load(ay, 0)[0]) for ay in ay_range]
Fz_inner = [W_wheel - (outer_wheel_load(ay, 0)[0] - W_wheel) for ay in ay_range]

ax1.plot(ay_range, Fz_outer, color=ORANGE, lw=2, label='Outer wheel')
ax1.plot(ay_range, Fz_inner, color=BLUE,   lw=2, label='Inner wheel')
ax1.axhline(W_wheel, color='gray', lw=1, ls='--', alpha=0.6, label=f'Static = {W_wheel:.0f} N')
ax1.axvline(1.5, color=RED, lw=1.2, ls=':', label='Design load 1.5g')
ax1.fill_between(ay_range, Fz_outer, W_wheel, alpha=0.1, color=ORANGE)
ax1.fill_between(ay_range, Fz_inner, W_wheel, alpha=0.1, color=BLUE)
ax1.set_xlabel('Lateral Acceleration [g]')
ax1.set_ylabel('Front Wheel Vertical Load Fz [N]')
ax1.set_title('Lateral Weight Transfer — Front Axle')
ax1.legend(fontsize=8)

ax_range = np.linspace(0, 2.0, 100)
F_uw_range = [wishbone_forces(*outer_wheel_load(ay, 0))[0] for ay in ax_range]
F_lw_range = [wishbone_forces(*outer_wheel_load(ay, 0))[1] for ay in ax_range]

ax2.plot(ax_range, F_uw_range, color=ORANGE, lw=2, label='Upper wishbone')
ax2.plot(ax_range, F_lw_range, color=BLUE,   lw=2, label='Lower wishbone')
ax2.axvline(1.5, color=RED, lw=1.2, ls=':', label='Design load 1.5g')
ax2.set_xlabel('Lateral Acceleration [g]')
ax2.set_ylabel('Wishbone Resultant Force [N]')
ax2.set_title('Wishbone Forces vs Lateral Acceleration')
ax2.legend(fontsize=8)

fig.suptitle('Porsche 911 (992) Front Suspension — Dynamic Load Analysis', fontsize=11, fontweight='bold')
fig.tight_layout()
fig.savefig('plots/02_weight_transfer.png')
plt.close(fig)
print('Saved: plots/02_weight_transfer.png')

# Plot 3: Suspension geometry schematic
fig, ax = plt.subplots(figsize=(8, 6))

# Ground line
ax.axhline(0, color='#888', lw=1.5, ls='-')
ax.fill_between([-0.1, track_f + 0.1], [-0.03, -0.03], [0, 0], color='#DDD')

# Tyre
theta = np.linspace(0, 2*np.pi, 100)
tx = half_t + tyre_r * np.cos(theta)
ty = tyre_r + tyre_r * np.sin(theta)
ax.plot(tx, ty, color='#333', lw=2)
ax.fill(tx, ty, alpha=0.1, color='#333')

# Upright (vertical line)
ax.plot([half_t]*2, [h_lw, h_uw + 0.04], color='#555', lw=4, solid_capstyle='round')

# Lower wishbone
ax.annotate('', xy=(half_t, h_lw), xytext=(0.05, h_lw),
            arrowprops=dict(arrowstyle='->', color=BLUE, lw=2))
ax.plot([0.05, half_t], [h_lw, h_lw], color=BLUE, lw=2.5)
ax.scatter([half_t, 0.05], [h_lw, h_lw], color=BLUE, s=40, zorder=5)
ax.text(0.25, h_lw + 0.015, f'Lower wishbone  L={l_lw*1000:.0f}mm', color=BLUE, fontsize=8.5)

# Upper wishbone — highlighted (this is what we design)
ax.plot([0.05 + (l_lw - l_uw)/2, half_t], [h_uw, h_uw], color=ORANGE, lw=3.5)
ax.scatter([half_t, 0.05 + (l_lw - l_uw)/2], [h_uw, h_uw], color=ORANGE, s=50, zorder=5)
ax.text(0.22, h_uw + 0.015, f'UPPER wishbone  L={l_uw*1000:.0f}mm  ← WE DESIGN THIS',
        color=ORANGE, fontsize=8.5, fontweight='bold')

# Forces at contact patch
F_scale = 0.00015
ax.annotate('', xy=(half_t, tyre_r - crit['Fz'] * F_scale),
            xytext=(half_t, tyre_r),
            arrowprops=dict(arrowstyle='->', color=RED, lw=2))
ax.text(half_t + 0.02, tyre_r - crit['Fz'] * F_scale / 2,
        f'Fz = {crit["Fz"]:.0f} N', color=RED, fontsize=8)

ax.annotate('', xy=(half_t - crit['Fy'] * F_scale, 0.05),
            xytext=(half_t, 0.05),
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=2))
ax.text(half_t - crit['Fy'] * F_scale - 0.04, 0.07,
        f'Fy = {crit["Fy"]:.0f} N', color=GREEN, fontsize=8)

# Dimension annotations
ax.annotate('', xy=(half_t, 0), xytext=(0, 0),
            arrowprops=dict(arrowstyle='<->', color='#888', lw=1))
ax.text(half_t/2, -0.025, f'Half track = {half_t*1000:.0f} mm', ha='center', fontsize=7.5, color='#666')

ax.annotate('', xy=(half_t + 0.08, h_uw), xytext=(half_t + 0.08, h_lw),
            arrowprops=dict(arrowstyle='<->', color='#888', lw=1))
ax.text(half_t + 0.10, (h_uw + h_lw)/2, f'{(h_uw - h_lw)*1000:.0f} mm', fontsize=7.5, color='#666')

ax.set_xlim(-0.08, 1.0)
ax.set_ylim(-0.08, 0.6)
ax.set_xlabel('Width from centreline [m]')
ax.set_ylabel('Height from ground [m]')
ax.set_title(f'Porsche 911 (992) Front Double Wishbone — Geometry & Critical Loads\n'
             f'Load case: Combined 1.2g lateral + 1.2g braking  |  F_upper = {crit["F_uw"]:.0f} N',
             fontsize=10)
ax.set_aspect('equal')
ax.grid(True, alpha=0.2)

fig.tight_layout()
fig.savefig('plots/03_suspension_geometry.png')
plt.close(fig)
print('Saved: plots/03_suspension_geometry.png')

print('\n✓ Phase 1 complete. Use the loads above as FEA boundary conditions.')
print('  → Next: model the upper wishbone A-arm in SolidWorks.')
