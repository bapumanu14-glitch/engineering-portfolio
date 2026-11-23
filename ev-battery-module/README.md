# EV Battery Module — Thermal Design & Validation

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243?logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.7+-11557C)
![ANSYS](https://img.shields.io/badge/ANSYS-2026_R1-FFB71B?logo=ansys&logoColor=black)
![Fusion 360](https://img.shields.io/badge/Fusion_360-CAD-E8601C)
![License](https://img.shields.io/badge/license-MIT-green)

A full thermal design workflow for a 15-cell Li-ion battery module, starting from first principles in Python and ending with finite element validation in ANSYS.

---

## Results at a glance

| Metric | Value | Limit | Status |
|--------|-------|--------|--------|
| Peak temperature (ANSYS FEA) | 42.2 °C | < 60 °C | ✅ PASS |
| Temperature gradient (ΔT) | 1.4 °C | < 5 °C | ✅ PASS |
| Max surface heat flux | 8054 W/m² | — | — |
| Python prediction (lumped) | 38.2 °C | — | ✅ PASS |
| Model agreement | 10.5 % | ≤ ±15 % | ✅ Within tolerance |

---

## Project overview

The module houses 15 × 21700 cylindrical Li-ion cells in a 3 × 5 grid inside an Aluminium 6061-T6 enclosure. At a 2C discharge rate each cell dissipates 2 W (I²R), giving a total heat load of 30 W. The project answers one question: what cooling strategy keeps every cell below 60 °C?

The workflow has four phases:

1. **Python thermal analysis**: analytical sizing, cooling strategy selection, transient response
2. **ISO engineering drawing**: three orthographic views with full dimensioning
3. **Fusion 360 CAD**: parametric housing with 15 cylindrical cell pockets
4. **ANSYS Steady-State Thermal FEA**: 3D validation with boundary conditions

---

## Module specifications

| Parameter | Value |
|-----------|-------|
| Cell format | 21700 Li-ion (cylindrical) |
| Arrangement | 3 × 5 grid (15 cells) |
| Housing material | Aluminium 6061-T6 |
| Module dimensions | 71 × 117 × 76 mm |
| Cell diameter / height | 21 mm / 70 mm |
| Pitch (centre to centre) | 23 mm |
| Pocket depth | 73 mm (3 mm floor) |
| Clearance, cell to wall | 2 mm |
| Thermal conductivity (k) | 160 W/mK |

---

## Thermal analysis (Python)

### Heat generation

```
Q_cell = I² × R = 10² × 0.020 = 2 W per cell
Q_total = 15 × 2 = 30 W
```

### Required convection coefficient

```
h_required = Q / (A_eff × ΔT_max)
           = 30 / (0.04519 m² × 20 °C)
           = 33.2 W/m²K
```

### Cooling strategy comparison

| Cooling Method | h (W/m²K) | T_max (°C) | Status |
|----------------|-----------|------------|--------|
| Natural convection | 8 | 91.4 | ❌ FAIL |
| **Forced air (selected)** | **50** | **38.2** | **✅ PASS** |
| Liquid cooling | 500 | 25.6 | ✅ PASS |

Forced air at h = 50 W/m²K gives a 17.8 °C thermal margin to the 60 °C limit.

### Biot number check

```
Bi = h × L_c / k = 50 × (0.021/6) / 160 = 0.0011
```

Bi << 0.1, so the lumped capacitance model is valid.

### Thermal time constants

| Scenario | τ (min) |
|----------|---------|
| Natural convection | 21.5 |
| Forced air | 4.3 |
| Liquid cooling | 0.4 |

---

## CAD model (Fusion 360)

Housing built as a parametric solid body with 15 cylindrical cell pockets.

**Workflow:**
1. Extrude solid box, 71 × 117 × 76 mm
2. Sketch 15 circles (Ø21 mm) on top face: 3 × 5 grid at 23 mm pitch, first centre at 12.5 mm from each outer wall
3. Extrude Cut 73 mm deep, leaving a 3 mm structural floor
4. No shell operation needed. The 2 mm clearance between cell and wall is defined by the pocket geometry itself

---

## ANSYS FEA setup

| Setting | Value |
|---------|-------|
| Analysis type | Steady-State Thermal |
| Solver | ANSYS 2026 R1 |
| Material | Aluminium Alloy NL (k = 160 W/mK, ρ = 2700 kg/m³, Cp = 875 J/kgK) |
| Heat Flow BC | 30 W total, applied to 15 pocket cylindrical surfaces |
| Convection BC | h = 50 W/m²K on 5 outer faces (top face open) |
| Mesh type | Tetrahedral |

### FEA results

```
T_max  =  42.2 °C  (centre column cells, hottest)
T_min  =  40.8 °C  (corner cells, cooled from two sides)
ΔT     =   1.4 °C  ← well within 5 °C limit
```

Max heat flux 8054 W/m² appears at the base of the centre column pockets, where the conduction path to a cooled face is longest.

---

## Repository structure

```
ev-battery-module/
├── battery_thermal.py             # Main Python analysis (172 lines)
├── EBM_Engineering_Drawing.svg    # ISO 2D drawing — vector format
├── EBM_Engineering_Drawing.html   # ISO 2D drawing — web embed
├── Code_Explained_EBM_Thermal.pdf # 16-page code walkthrough
├── EBM_Portfolio_Report.pdf       # Portfolio summary (this project)
└── README.md
```

---

## Running the Python analysis

**Requirements:**

```bash
pip install numpy matplotlib
```

**Run:**

```bash
python battery_thermal.py
```

The script outputs:

- Required convection coefficient (h_req)
- Temperature for three cooling strategies
- Biot number validation
- Thermal time constants (τ) for each strategy
- Matplotlib plots: cooling comparison bar chart, transient response curves

---

## Engineering decisions

**Why forced air and not liquid cooling?**
Liquid cooling gets down to 25.6 °C but doubles system complexity and adds leak risk. Forced air at 38.2 °C still leaves a 22 °C margin below the 60 °C limit, plus another 17.8 °C beyond that. For a module running at 2C discharge, forced air is the better choice.

**Why Al 6061-T6?**
High thermal conductivity (160 W/mK), good machinability for the pocket features, and enough strength for automotive vibration loads. The 2 mm wall clearance and 3 mm floor both sit within typical CNC tolerances.

**Python vs ANSYS — why is there a 10.5% difference?**
The lumped model treats the housing as isothermal, so it can't capture 3D corner heat flux concentration or the effect of the open top face reducing effective cooling area. The 10.5% gap falls within the ±15% tolerance expected from analytical models, and both methods reach the same design conclusion anyway.

---

## Skills demonstrated

- Heat transfer theory: Newton's Law of Cooling, Joule heating, Biot number, lumped capacitance
- Python: numerical modelling, NumPy, Matplotlib, structured output
- CAD: Fusion 360 parametric design, Extrude Cut operations, tolerancing for real assembly
- FEA: ANSYS Steady-State Thermal, mesh generation, boundary condition setup, result interpretation
- Engineering drawing: ISO orthographic projection across three views, GD&T callouts

---

## Author

**Bapu Manu**
M.Eng. Student · SRH Berlin
bapumanu14@gmail.com

---

*Part of an EV/automotive engineering portfolio targeting graduate and junior roles in battery systems, thermal management, and structural simulation.*
