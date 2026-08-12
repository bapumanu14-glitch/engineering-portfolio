"""
fluent_cfd_post.py
------------------
Automated post-processing for ANSYS Fluent CFD results.

Reads CSV exports from Fluent (residuals, XY data, force history) and
produces publication-quality plots saved to the plots/ directory.

HOW TO EXPORT DATA FROM FLUENT
-------------------------------
Residuals:
  Monitors → Residuals → right-click → Export → residuals.csv

Cp / Cf / y+ along surfaces:
  Plots → XY Plot → choose variable → File → cp_body.csv

Force history:
  Monitors → Force Monitors → CD / CL → Export → forces.csv

Usage:
  python fluent_cfd_post.py                   # uses data/ folder
  python fluent_cfd_post.py --data /my/path   # custom data folder

Author: Bapu Manu | HAW Hamburg | July 2026
"""

import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# ── Plot style ────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':       'DejaVu Sans',
    'font.size':         10,
    'axes.titlesize':    11,
    'axes.titleweight':  'bold',
    'axes.labelsize':    10,
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'axes.grid':         True,
    'grid.alpha':        0.3,
    'grid.linestyle':    '--',
    'lines.linewidth':   1.8,
    'figure.dpi':        150,
    'savefig.dpi':       200,
    'savefig.bbox':      'tight',
})

BLUE    = '#1B3A6B'
ORANGE  = '#E07B39'
GREEN   = '#2E8B57'
RED     = '#C0392B'
PURPLE  = '#7D3C98'
TEAL    = '#17A589'
GRAY    = '#7F8C8D'


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_residuals(path):
    """
    Load Fluent residuals CSV.
    Expected columns: Iteration, continuity, x-velocity, y-velocity, k, omega
    (column names vary — auto-detected)
    """
    df = pd.read_csv(path, comment='#')
    df.columns = [c.strip().lower() for c in df.columns]
    return df


def load_xy_data(path):
    """
    Load Fluent XY Plot export.
    Format: two columns — Position (m), Variable value
    """
    df = pd.read_csv(path, comment='#')
    df.columns = [c.strip() for c in df.columns]
    return df


def load_force_history(path):
    """
    Load Fluent force monitor CSV.
    Expected columns: Iteration, Cd (or Cl)
    """
    df = pd.read_csv(path, comment='#')
    df.columns = [c.strip().lower() for c in df.columns]
    return df


# ── Synthetic data generator (Ahmed body, k-omega SST, 40 m/s) ────────────────

def generate_sample_data(data_dir):
    """
    Generate realistic synthetic Ahmed body CFD data matching the
    ANSYS Fluent 2026 R1 simulation results (Cd=0.938, Cl=9.22, 29k cells).
    Replace these files with real Fluent exports to use actual data.
    """
    rng = np.random.default_rng(42)
    n   = 92   # iterations to convergence

    # ── Residuals ─────────────────────────────────────────────────────────────
    iters = np.arange(1, n + 1)
    def decay(start, end, noise=0.08):
        t = np.linspace(0, 1, n)
        base = start * np.exp((np.log(end) - np.log(start)) * t)
        return base * np.exp(rng.normal(0, noise, n))

    res = pd.DataFrame({
        'iteration':  iters,
        'continuity': decay(1e0,  8e-4),
        'x-velocity': decay(1e0,  3e-5),
        'y-velocity': decay(1e0,  2e-5),
        'k':          decay(1e0,  6e-5),
        'omega':      decay(1e0,  4e-5),
    })
    res.to_csv(Path(data_dir) / 'residuals.csv', index=False)

    # ── Cp along car body ─────────────────────────────────────────────────────
    # x/L from 0 (front) to 1 (rear base)
    x = np.linspace(0, 1.0, 300)
    cp = np.zeros_like(x)

    # Stagnation zone (front face, x ~ 0–0.02)
    mask_front = x < 0.02
    cp[mask_front] = 1.30 - 15 * x[mask_front]

    # Nose corner suction (x ~ 0.02–0.08)
    mask_nose = (x >= 0.02) & (x < 0.08)
    t = (x[mask_nose] - 0.02) / 0.06
    cp[mask_nose] = -4.0 + 4.5 * t

    # Roof plateau (x ~ 0.08–0.65)
    mask_roof = (x >= 0.08) & (x < 0.65)
    cp[mask_roof] = -1.0 + 0.15 * (x[mask_roof] - 0.08) + rng.normal(0, 0.02, mask_roof.sum())

    # Rear slant pressure recovery (x ~ 0.65–0.85)
    mask_slant = (x >= 0.65) & (x < 0.85)
    t = (x[mask_slant] - 0.65) / 0.20
    cp[mask_slant] = -1.0 + 1.4 * t + rng.normal(0, 0.03, mask_slant.sum())

    # Base (x ~ 0.85–1.0)
    mask_base = x >= 0.85
    cp[mask_base] = 0.40 + rng.normal(0, 0.02, mask_base.sum())

    cp_df = pd.DataFrame({'x_over_L': x, 'Cp': cp})
    cp_df.to_csv(Path(data_dir) / 'cp_body.csv', index=False)

    # ── y+ along car body ─────────────────────────────────────────────────────
    yplus = np.zeros_like(x)
    # Stagnation — low y+ (flow slows)
    yplus[mask_front] = 0.4 + rng.uniform(0, 0.3, mask_front.sum())
    # Nose corner — high skin friction → higher y+
    yplus[mask_nose]  = 3.5 - 2.0 * (x[mask_nose] - 0.02) / 0.06 + rng.uniform(0, 0.3, mask_nose.sum())
    # Roof — boundary layer grows, y+ moderate
    yplus[mask_roof]  = 1.8 + 0.5 * np.sin(np.pi * (x[mask_roof] - 0.08) / 0.57) + rng.uniform(0, 0.3, mask_roof.sum())
    # Slant — lower y+
    yplus[mask_slant] = 1.2 + rng.uniform(0, 0.4, mask_slant.sum())
    # Base — very low (flow separated)
    yplus[mask_base]  = 0.6 + rng.uniform(0, 0.3, mask_base.sum())

    yp_df = pd.DataFrame({'x_over_L': x, 'y_plus': yplus})
    yp_df.to_csv(Path(data_dir) / 'yplus_body.csv', index=False)

    # ── Force coefficient history ──────────────────────────────────────────────
    cd_conv = 0.938 + 0.5 * np.exp(-0.08 * iters) + rng.normal(0, 0.003, n)
    cl_conv = 9.22  + 4.0 * np.exp(-0.07 * iters) + rng.normal(0, 0.02, n)

    forces = pd.DataFrame({'iteration': iters, 'cd': cd_conv, 'cl': cl_conv})
    forces.to_csv(Path(data_dir) / 'forces.csv', index=False)

    # ── Wake velocity profile (at x = 1.5L behind car) ───────────────────────
    y_norm = np.linspace(-0.5, 2.0, 200)   # y / H  (H = car height)
    u_norm = np.ones_like(y_norm)

    # Wake deficit behind car body (y/H = 0 to 1)
    wake_mask = (y_norm >= 0) & (y_norm <= 1.2)
    t = y_norm[wake_mask]
    u_norm[wake_mask] = 0.55 + 0.45 * np.sin(np.pi * t / 1.2) ** 0.4

    # Slight velocity overshoot above roof
    over_mask = (y_norm > 1.2) & (y_norm < 1.6)
    u_norm[over_mask] = 1.0 + 0.05 * np.exp(-((y_norm[over_mask] - 1.35) ** 2) / 0.02)

    # Ground boundary layer
    bl_mask = y_norm < 0
    u_norm[bl_mask] = np.maximum(0, 1.0 + y_norm[bl_mask] * 1.5)

    wake_df = pd.DataFrame({'y_over_H': y_norm, 'u_over_Uinf': u_norm})
    wake_df.to_csv(Path(data_dir) / 'wake_velocity.csv', index=False)

    print(f'Sample data written to {data_dir}')
    return data_dir


# ── Plotting functions ─────────────────────────────────────────────────────────

def plot_convergence(data_dir, out_dir):
    path = Path(data_dir) / 'residuals.csv'
    if not path.exists():
        print(f'  [skip] {path} not found'); return

    df  = load_residuals(path)
    col = [c for c in df.columns if c != 'iteration']
    it  = df['iteration']

    palette = [BLUE, ORANGE, GREEN, RED, PURPLE, TEAL]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, c in enumerate(col):
        ax.semilogy(it, df[c], label=c.capitalize(), color=palette[i % len(palette)])

    ax.axhline(1e-3, ls=':', lw=1.2, color=GRAY, label='Convergence criterion (10⁻³)')
    ax.set_xlabel('Iteration')
    ax.set_ylabel('Scaled Residual')
    ax.set_title('Residual Convergence History — Ahmed Body CFD (k-ω SST)')
    ax.legend(fontsize=8, ncol=2)
    ax.set_xlim(left=1)

    conv_iter = it[df[col[0]] < 1e-3].iloc[0] if (df[col[0]] < 1e-3).any() else None
    if conv_iter:
        ax.axvline(conv_iter, ls='--', lw=1, color=GRAY, alpha=0.6)
        ax.text(conv_iter + 1, ax.get_ylim()[0] * 3, f'Converged\n@ iter {conv_iter}',
                fontsize=7.5, color=GRAY)

    fig.tight_layout()
    out = Path(out_dir) / '01_convergence.png'
    fig.savefig(out)
    plt.close(fig)
    print(f'  Saved: {out}')


def plot_cp(data_dir, out_dir):
    path = Path(data_dir) / 'cp_body.csv'
    if not path.exists():
        print(f'  [skip] {path} not found'); return

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(df['x_over_L'], df['Cp'], color=BLUE, lw=1.8)
    ax.axhline(0, color=GRAY, lw=0.8, ls='--')
    ax.axhline(1.3,  color=ORANGE, lw=0.8, ls=':', alpha=0.7)
    ax.axhline(-4.0, color=RED,    lw=0.8, ls=':', alpha=0.7)

    ax.annotate('Stagnation\n(Cp ≈ +1.3)', xy=(0.01, 1.30),
                xytext=(0.08, 1.6), arrowprops=dict(arrowstyle='->', color=GRAY), fontsize=8)
    ax.annotate('Nose suction\npeak (Cp ≈ −4.0)', xy=(0.04, -3.9),
                xytext=(0.18, -3.4), arrowprops=dict(arrowstyle='->', color=GRAY), fontsize=8)
    ax.annotate('Roof plateau\n(Cp ≈ −1.0)', xy=(0.38, -1.0),
                xytext=(0.32, -1.9), arrowprops=dict(arrowstyle='->', color=GRAY), fontsize=8)
    ax.annotate('Slant\nrecovery', xy=(0.75, -0.35),
                xytext=(0.70, -2.0), arrowprops=dict(arrowstyle='->', color=GRAY), fontsize=8)

    ax.invert_yaxis()
    ax.set_xlabel('x / L  (0 = front, 1 = rear base)')
    ax.set_ylabel('Pressure Coefficient  Cp  [ − ]')
    ax.set_title('Cp Distribution Along Ahmed Body Surface — k-ω SST, Re = 2.74 × 10⁶')

    for label, xpos in [('Front', 0.01), ('Roof', 0.38), ('Slant', 0.73), ('Base', 0.92)]:
        ax.axvline(xpos, color=GRAY, lw=0.5, ls=':', alpha=0.5)
        ax.text(xpos + 0.005, ax.get_ylim()[1] * 0.97, label, fontsize=7, color=GRAY)

    fig.tight_layout()
    out = Path(out_dir) / '02_cp_distribution.png'
    fig.savefig(out)
    plt.close(fig)
    print(f'  Saved: {out}')


def plot_yplus(data_dir, out_dir):
    path = Path(data_dir) / 'yplus_body.csv'
    if not path.exists():
        print(f'  [skip] {path} not found'); return

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.fill_between(df['x_over_L'], df['y_plus'], alpha=0.2, color=BLUE)
    ax.plot(df['x_over_L'], df['y_plus'], color=BLUE, lw=1.8)
    ax.axhline(5, color=RED, lw=1.2, ls='--', label='y⁺ = 5  (wall-resolved limit)')
    ax.axhline(1, color=GREEN, lw=1.0, ls=':', label='y⁺ = 1  (ideal)')

    ax.set_ylim(0, 6)
    ax.set_xlabel('x / L  (0 = front, 1 = rear base)')
    ax.set_ylabel('Wall y⁺  [ − ]')
    ax.set_title('Wall y⁺ Distribution — First Cell Height = 1 × 10⁻⁵ m, 15 Inflation Layers')
    ax.legend(fontsize=8)

    yp = df['y_plus']
    ax.text(0.98, 0.97,
            f'Max y⁺ = {yp.max():.2f}\nMean y⁺ = {yp.mean():.2f}\nMin y⁺ = {yp.min():.2f}',
            transform=ax.transAxes, va='top', ha='right', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.4', fc='white', ec=GRAY, alpha=0.8))

    fig.tight_layout()
    out = Path(out_dir) / '03_yplus_distribution.png'
    fig.savefig(out)
    plt.close(fig)
    print(f'  Saved: {out}')


def plot_force_history(data_dir, out_dir):
    path = Path(data_dir) / 'forces.csv'
    if not path.exists():
        print(f'  [skip] {path} not found'); return

    df = pd.read_csv(path)
    it = df['iteration']

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    ax1.plot(it, df['cd'], color=BLUE, lw=1.8)
    ax1.axhline(0.938, color=ORANGE, lw=1.2, ls='--', label='Final Cd = 0.938')
    ax1.axhline(0.285, color=GREEN,  lw=1.0, ls=':', label='Experimental 3D Cd = 0.285')
    ax1.set_ylabel('Drag Coefficient  Cd')
    ax1.set_title('Force Coefficient Convergence — Ahmed Body, k-ω SST')
    ax1.legend(fontsize=8)

    ax2.plot(it, df['cl'], color=RED, lw=1.8)
    ax2.axhline(9.22, color=ORANGE, lw=1.2, ls='--', label='Final Cl = 9.22')
    ax2.set_xlabel('Iteration')
    ax2.set_ylabel('Lift Coefficient  Cl')
    ax2.legend(fontsize=8)

    note = ('Note: Cd over-prediction vs experiment is expected in 2D.\n'
            'Lateral flow relief and C-pillar vortices absent in 2D domain.')
    fig.text(0.5, 0.01, note, ha='center', fontsize=7.5, color=GRAY, style='italic')

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    out = Path(out_dir) / '04_force_history.png'
    fig.savefig(out)
    plt.close(fig)
    print(f'  Saved: {out}')


def plot_wake_velocity(data_dir, out_dir):
    path = Path(data_dir) / 'wake_velocity.csv'
    if not path.exists():
        print(f'  [skip] {path} not found'); return

    df = pd.read_csv(path)

    fig, ax = plt.subplots(figsize=(5, 7))
    ax.plot(df['u_over_Uinf'], df['y_over_H'], color=BLUE, lw=2.0)
    ax.fill_betweenx(df['y_over_H'], df['u_over_Uinf'], 1.0, alpha=0.12, color=BLUE)
    ax.axvline(1.0, color=GRAY, lw=1.0, ls='--', alpha=0.6, label='Freestream')
    ax.axhline(0.0, color=GRAY, lw=0.8, ls=':')
    ax.axhline(1.0, color=GRAY, lw=0.8, ls=':')

    ax.text(0.56, 0.5,  'Wake\ndeficit', fontsize=8, color=BLUE, ha='center')
    ax.text(1.04, 0.0,  'Ground', fontsize=7.5, color=GRAY, va='bottom')
    ax.text(1.04, 1.0,  'Roof',   fontsize=7.5, color=GRAY, va='bottom')

    ax.set_xlabel('u / U∞  (velocity normalised by freestream)')
    ax.set_ylabel('y / H  (height normalised by car height)')
    ax.set_title('Wake Velocity Profile\n@ x = 1.5L behind car  |  Ahmed Body CFD')
    ax.legend(fontsize=8)
    ax.set_xlim(0, 1.2)

    fig.tight_layout()
    out = Path(out_dir) / '05_wake_velocity.png'
    fig.savefig(out)
    plt.close(fig)
    print(f'  Saved: {out}')


# ── Summary stats ─────────────────────────────────────────────────────────────

def print_summary(data_dir):
    print('\n' + '='*55)
    print('  CFD POST-PROCESSING SUMMARY — Ahmed Body (2D, k-ω SST)')
    print('='*55)

    f_path = Path(data_dir) / 'forces.csv'
    if f_path.exists():
        df  = pd.read_csv(f_path)
        cd  = df['cd'].iloc[-1]
        cl  = df['cl'].iloc[-1]
        print(f'  Final Cd           : {cd:.4f}')
        print(f'  Final Cl           : {cl:.4f}')
        print(f'  Cd vs experiment   : {cd:.4f} vs 0.285  ({(cd/0.285-1)*100:+.0f}% — 2D assumption)')

    r_path = Path(data_dir) / 'residuals.csv'
    if r_path.exists():
        df   = load_residuals(r_path)
        iters = len(df)
        print(f'  Iterations         : {iters}')
        col = [c for c in df.columns if c != 'iteration']
        for c in col:
            print(f'  Final {c:<16}: {df[c].iloc[-1]:.2e}')

    yp_path = Path(data_dir) / 'yplus_body.csv'
    if yp_path.exists():
        df = pd.read_csv(yp_path)
        print(f'  y+ (max/mean/min)  : {df.y_plus.max():.2f} / {df.y_plus.mean():.2f} / {df.y_plus.min():.2f}')

    print('='*55 + '\n')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='ANSYS Fluent CFD Post-Processor')
    parser.add_argument('--data',  default='data',  help='Path to Fluent export CSVs')
    parser.add_argument('--out',   default='plots', help='Output directory for plots')
    parser.add_argument('--sample', action='store_true',
                        help='Generate synthetic Ahmed body sample data first')
    args = parser.parse_args()

    data_dir = Path(args.data)
    out_dir  = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate sample data if requested or if no data exists
    if args.sample or not any(data_dir.glob('*.csv')):
        print('Generating synthetic Ahmed body sample data...')
        generate_sample_data(data_dir)

    print(f'\nPost-processing data from: {data_dir.resolve()}')
    print(f'Saving plots to:           {out_dir.resolve()}\n')

    plot_convergence(data_dir, out_dir)
    plot_cp(data_dir, out_dir)
    plot_yplus(data_dir, out_dir)
    plot_force_history(data_dir, out_dir)
    plot_wake_velocity(data_dir, out_dir)

    print_summary(data_dir)
    print(f'All plots saved to {out_dir.resolve()}')


if __name__ == '__main__':
    main()
