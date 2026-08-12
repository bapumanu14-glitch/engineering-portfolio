import numpy as np
import matplotlib.pyplot as plt

#  CELL SPECIFICATIONS: Tesla 21700 
capacity_Ah = 5.0      # Ah  — cell capacity
V_nominal   = 3.7      # V   — nominal voltage
R_internal  = 0.020    # Ohm — internal resistance (20 mΩ)
C_rate      = 2.0      # 2C  — fast charge / hard acceleration
#  HEAT GENERATION PER CELL 
I_cell    = C_rate * capacity_Ah     # current per cell (A)
P_heat    = I_cell**2 * R_internal   # heat generated (W)
P_elec    = I_cell * V_nominal       # electrical power (W)
efficiency = 1 - (P_heat / P_elec)   # cell efficiency at this C-rate

print(f"Discharge current     = {I_cell:.1f} A")
print(f"Heat per cell         = {P_heat:.2f} W")
print(f"Electrical power      = {P_elec:.2f} W")
print(f"Cell efficiency       = {efficiency*100:.1f} %")
# ── MODULE SPECIFICATIONS (3 × 5 = 15 cells) ──────────────────
n_cells     = 15
n_cols      = 3
n_rows      = 5

# Cell geometry (21700 format)
d_cell      = 21e-3      # diameter in metres
h_cell      = 70e-3      # height in metres
gap         = 2e-3       # gap between cells (mm)

# Module total heat load
Q_total     = n_cells * P_heat
print(f"\nModule total heat     = {Q_total:.1f} W")
print(f"Heat per cell         = {P_heat:.2f} W")

# Module dimensions (aluminium frame)
L_module = n_cols * (d_cell + gap) + gap   # width
W_module = n_rows * (d_cell + gap) + gap   # depth
H_module = h_cell + 2 * 3e-3              # height (cell + 3mm top/bottom wall)

print(f"\nModule size: {L_module*1000:.1f} mm × {W_module*1000:.1f} mm × {H_module*1000:.1f} mm")
# ── THERMAL MODEL — steady-state temperature rise ──────────────
T_ambient   = 25.0       # °C — surrounding air temperature
h_conv      = 10.0       # W/m²K — natural convection (still air)

# Surface area of module (all 6 faces)
A_surface = 2 * (L_module*W_module + L_module*H_module + W_module*H_module)

# Maximum temperature rise (all heat via convection from outer surface)
delta_T     = Q_total / (h_conv * A_surface)
T_surface   = T_ambient + delta_T

# Cell core is hotter than surface (conduction resistance through Al wall)
k_aluminium = 160.0      # W/mK — thermal conductivity
t_wall      = 3e-3       # m — wall thickness
R_cond      = t_wall / (k_aluminium * A_surface)
T_cell_max  = T_surface + Q_total * R_cond

print(f"\nSurface area          = {A_surface*1e6:.0f} mm²")
print(f"Temperature rise      = {delta_T:.1f} °C")
print(f"Module surface temp   = {T_surface:.1f} °C")
print(f"Max cell temperature  = {T_cell_max:.1f} °C")

if T_cell_max > 45:
    print("WARNING: Cells exceed 45°C — active cooling required")
else:
    print("OK: Natural convection is sufficient")
    # ── REQUIRED COOLING COEFFICIENT ──────────────────────────────
T_cell_limit = 45.0      # °C — max safe cell temperature

delta_T_max  = T_cell_limit - T_ambient     # = 20°C allowable rise
h_required   = Q_total / (delta_T_max * A_surface)

# Compare cooling methods
cooling = {
    "Natural convection (still air)": 10,
    "Forced air (fan)":               50,
    "Liquid cooling (glycol)":        500,
    "Required (to stay < 45°C)":      round(h_required, 1),
}

print(f"\nRequired h to stay below 45°C = {h_required:.1f} W/m²K")
print(f"\nCooling method comparison:")
for method, h in cooling.items():
    T_max = T_ambient + Q_total / (h * A_surface)
    status = "OK" if T_max <= 45 else "FAIL"
    print(f"  {method:<40} h={h:>5} W/m²K → T={T_max:.1f}°C  [{status}]")
    # ── VISUALISATION ──────────────────────────────────────────────
h_vals   = [10,  33.2, 50,  500]
T_vals   = [T_ambient + Q_total/(h*A_surface) for h in h_vals]
labels   = ["Natural\nconvection", "Minimum\nrequired", "Forced air\n(fan)", "Liquid\ncooling"]
colors   = ["#e74c3c", "#f39c12", "#2ecc71", "#3498db"]

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(labels, T_vals, color=colors, width=0.5, edgecolor="black", linewidth=0.5)
ax.axhline(45, color="red", linestyle="--", linewidth=1.5, label="45°C cell limit")
ax.axhline(25, color="gray", linestyle=":", linewidth=1, label="Ambient (25°C)")

for bar, T in zip(bars, T_vals):
    ax.text(bar.get_x()+bar.get_width()/2, T+1, f"{T:.1f}°C",
            ha="center", va="bottom", fontsize=10, fontweight="bold")

ax.set_ylabel("Max Cell Temperature (°C)", fontsize=11)
ax.set_title("EV Battery Module — Cooling Strategy Comparison\n"
             "15× 21700 cells, 2C rate, 30 W total heat", fontsize=12)
ax.set_ylim(0, 105)
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("cooling_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("Plot saved.")
# ── TRANSIENT ANALYSIS — temperature vs time ────────────────────
# Thermal mass of the module
m_cells   = 15 * 70e-3          # 15 cells × 70 g each = 1.05 kg
cp_cells  = 1000                # J/kg·K  (mixed cell materials)
rho_Al    = 2700; cp_Al = 900   # kg/m³, J/kg·K
V_module  = L_module*W_module*H_module
V_cells   = 15 * np.pi/4 * d_cell**2 * h_cell
V_Al      = V_module - V_cells
m_Al      = rho_Al * V_Al
C_total   = m_cells*cp_cells + m_Al*cp_Al   # J/K — total heat capacity

t = np.linspace(0, 7200, 1000)   # 0 to 2 hours in seconds

def T_transient(h_conv):
    hA = h_conv * A_surface
    tau = C_total / hA
    dT_ss = Q_total / hA
    return T_ambient + dT_ss * (1 - np.exp(-t / tau))

T_nat   = T_transient(10)
T_fan   = T_transient(50)
T_liq   = T_transient(500)

print(f"Thermal mass   = {C_total:.0f} J/K")
print(f"Time constant natural convection = {C_total/(10*A_surface)/60:.1f} min")
print(f"Time constant forced air         = {C_total/(50*A_surface)/60:.1f} min")

fig2, ax2 = plt.subplots(figsize=(9, 5))
ax2.plot(t/60, T_nat, color="#e74c3c", label="Natural convection (h=10)")
ax2.plot(t/60, T_fan, color="#2ecc71", label="Forced air fan (h=50)")
ax2.plot(t/60, T_liq, color="#3498db", label="Liquid cooling (h=500)")
ax2.axhline(45, color="red", linestyle="--", linewidth=1.5, label="45°C cell limit")
ax2.set_xlabel("Time (minutes)", fontsize=11)
ax2.set_ylabel("Max Cell Temperature (°C)", fontsize=11)
ax2.set_title("EV Battery Module — Thermal Transient Response\n"
              "15× 21700 cells, 2C discharge rate", fontsize=12)
ax2.legend(fontsize=10)
ax2.grid(alpha=0.3)
ax2.set_xlim(0, 120)
plt.tight_layout()
plt.savefig("thermal_transient.png", dpi=150, bbox_inches="tight")
plt.show()
print("Transient plot saved.")
# ── FINAL ENGINEERING SUMMARY ──────────────────────────────────
print("\n" + "="*55)
print("  EV BATTERY MODULE — THERMAL ANALYSIS SUMMARY")
print("="*55)
print(f"  Cell type          : 21700 Li-ion, 5 Ah, 3.7 V")
print(f"  Module layout      : {n_rows}×{n_cols} cells ({n_cells} total)")
print(f"  Module dimensions  : {L_module*1e3:.0f} × {W_module*1e3:.0f} × {H_module*1e3:.0f} mm")
print(f"  Discharge rate     : {C_rate}C  ({I_cell:.0f} A per cell)")
print(f"  Total heat load    : {Q_total:.1f} W")
print(f"  Cell efficiency    : {efficiency*100:.1f}%")
print("-"*55)
print(f"  Natural convection : T = {T_ambient + Q_total/(10*A_surface):.1f}°C  → FAILS (limit 45°C)")
print(f"  Minimum h required : {h_required:.1f} W/m²K")
print(f"  Forced air (fan)   : T = {T_ambient + Q_total/(50*A_surface):.1f}°C  → SAFE")
print(f"  Liquid cooling     : T = {T_ambient + Q_total/(500*A_surface):.1f}°C  → SAFE (best)")
print("-"*55)
print(f"  RECOMMENDATION: Minimum forced-air cooling required.")
print(f"  For battery longevity, liquid cooling recommended.")
print("="*55)