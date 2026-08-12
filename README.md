# Engineering Portfolio — Bapu Manu

MSc Student, SRH Berlin University of Applied Sciences · bapumanu2001@gmail.com

Four CAE and simulation projects covering thermal design, structural FEA, fatigue analysis, and CFD post-processing — each built as a full workflow from first-principles Python analysis through CAD to finite element validation.

---

## Projects

### 🔋 [EV Battery Module — Thermal Design & Validation](ev-battery-module/)
15-cell Li-ion battery module thermal design. Python heat transfer analysis → Fusion 360 CAD → ANSYS Steady-State Thermal FEA.
**Result:** 42.2 °C peak temperature, PASS against 60 °C limit.

### 🏎️ [Porsche 992 GT3 Front Upper Wishbone — Structural FEA](porsche-911-wishbone/)
Vehicle dynamics load derivation → Fusion 360 A-arm modelling → ANSYS static structural FEA.
**Result:** current tube geometry fails at 1.5× yield under combined cornering/braking; design fix identified (20 mm → 25 mm OD).

### ⚙️ [Porsche 992 PDK Input Shaft — Fatigue Life Analysis](porsche-pdk-shaft/)
Modified Goodman fatigue analysis (Python) cross-validated against ANSYS static FEA.
**Result:** shaft passes static yield (FoS 1.88–1.90, <1% agreement between methods) but fails the fatigue criterion (Goodman FoS 0.84) — a failure mode invisible to static FEA alone.

### 💨 [Ahmed Body — CFD Post-Processing](cfd-post-processor/)
Automated post-processing pipeline for ANSYS Fluent CFD results on the Ahmed body benchmark geometry.

---

## Tools & methods across projects

`Python` `NumPy` `Matplotlib` `Fusion 360` `ANSYS Mechanical 2026 R1` `ANSYS Fluent`

Heat transfer · structural FEA · fatigue analysis (Modified Goodman, Marin factors) · vehicle dynamics · CFD post-processing · ISO engineering drawings

Every project follows the same pattern: derive the physics from first principles in Python, build the geometry in CAD, validate with FEA/CFD, and cross-check the numerical result against the analytical one. Where the two disagree, the gap gets explained rather than papered over — the wishbone and PDK shaft projects both surfaced real design failures, not just clean passes.

---

## Author

**Bapu Manu**
MSc Sustainable Technology Management — Automotive, SRH Berlin
bapumanu2001@gmail.com

---

*Looking for Werkstudent / graduate roles in CAE, structural simulation, thermal design, or vehicle dynamics.*
