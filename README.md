# Engineering Portfolio — Bapu Manu

M.Eng. Student, SRH Berlin University of Applied Sciences · bapumanu14@gmail.com

Six CAE and simulation projects covering thermal design, structural FEA, fatigue analysis, CFD post processing, battery management systems, and e-drive design. Most run the same workflow: first principles analysis in Python, geometry in CAD, then validation with finite element or CFD tools. The BMS and traction motor projects run the algorithmic and electromagnetic side of the powertrain: state estimation and motor design instead of geometry.

---

## Projects

### 🔋 [EV Battery Module — Thermal Design & Validation](ev-battery-module/)
15-cell Li-ion battery module thermal design. Python heat transfer analysis, Fusion 360 CAD, ANSYS Steady-State Thermal FEA.
**Result:** 42.2 °C peak temperature, PASS against the 60 °C limit.

### 🔌 [EV Battery BMS — State of Charge & State of Health Estimation](ev-battery-bms/)
Extended Kalman Filter SoC estimation against naive Coulomb counting, plus a capacity fade model, on the same cell used in the battery module project.
**Result:** EKF holds 0.34 pp RMSE versus 0.84 pp for Coulomb counting, and recovers from a 10 point injected error in about 20 seconds.

### 🧲 [EV Traction Motor — Torque-Speed Envelope, Efficiency, and Thermal Analysis](ev-traction-motor/)
IPMSM electromagnetic and thermal modelling grounded in a real measured teardown of the Tesla Model 3 rear drive motor.
**Result:** 97.5% peak efficiency, winding temperature holds 12 °C below the design limit under a demanding synthetic drive cycle, with thermal foldback engaging correctly during hard acceleration.

### 🏎️ [Porsche 992 GT3 Front Upper Wishbone — Structural FEA](porsche-911-wishbone/)
Vehicle dynamics load derivation, Fusion 360 A-arm modelling, ANSYS static structural FEA.
**Result:** the current tube geometry fails at 1.5× yield under combined cornering and braking. Design fix identified: 20 mm to 25 mm OD.

### ⚙️ [Porsche 992 PDK Input Shaft — Fatigue Life Analysis](porsche-pdk-shaft/)
Modified Goodman fatigue analysis in Python, checked against ANSYS static FEA.
**Result:** shaft passes static yield (FoS 1.88–1.90, under 1% difference between methods) but fails the fatigue criterion (Goodman FoS 0.84), a failure mode static FEA alone can't see.

### 💨 [Ahmed Body — CFD Post Processing](cfd-post-processor/)
A post processing pipeline for ANSYS Fluent CFD results on the Ahmed body benchmark geometry.

---

## Tools & methods across projects

`Python` `NumPy` `Matplotlib` `Fusion 360` `ANSYS Mechanical 2026 R1` `ANSYS Fluent`

Heat transfer · structural FEA · fatigue analysis (Modified Goodman, Marin factors) · vehicle dynamics · CFD post processing · battery state estimation (Extended Kalman Filter) · electric machine design and thermal modelling · ISO engineering drawings

Where the analytical and numerical results disagree, the gap gets explained rather than smoothed over. The wishbone and PDK shaft projects both turned up real design failures, not just clean passes.

---

## Author

**Bapu Manu**
M.Eng. Sustainable Technology Management — Automotive, SRH Berlin
bapumanu14@gmail.com

---

*Looking for graduate and junior roles in CAE, structural simulation, thermal design, or vehicle dynamics.*
