#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch processing script for polar 2D slicing and plotting across all task folders.

Written by Guanshihan Du on 2025-06-25

This script automates the aggregation of 3D polar field data from chunk files,
extracts 2D slices in specified planes, and generates quiver plots for visualization.
It processes each task directory under a base folder, handling data reading,
optional full-data output, slicing indices, interpolation, plotting, and summary.
"""
import os
import shutil
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt

################# USER CONFIG ##################
BASE_DIR        = 'tasks'             # Root directory containing task_* subfolders
TIME_STEP       = 500                   # Base index for the first data chunk
NUM_CHUNKS      = 20                  # Number of chunk files per time step
DAT_PATTERN     = 'PELOOP.%08d.dat'   # Filename pattern for chunk data (index = TIME_STEP + chunk)

# Toggle full 3D data output
WRITE_PXYZ      = False               # Set to False to skip writing full 3D data file

# Slicing indices (1-based). None selects the mid-plane dimension.
XY_SLICE_K      = 150                 # Z-index for XY slice
XZ_J_INDEX      = None                # Y-index for XZ slice
YZ_I_INDEX      = None                # X-index for YZ slice

# Plot configuration for XY plane
XY_INTERP_NUM   = 50                  # Number of interpolation points in X
XY_INTERP_NUM2  = 50                  # Number of interpolation points in Y
XY_DPI          = 500                 # Output image resolution (dots per inch)
XY_X_MIN, XY_X_MAX = 1, 100           # X-axis domain limits for interpolation/grid
XY_Y_MIN, XY_Y_MAX = 1, 100           # Y-axis domain limits for interpolation/grid
XY_COLOR        = 'blue'              # Quiver arrow color

# Plot configuration for XZ plane
XZ_INTERP_NUM   = 50                  # Number of interpolation points in X
XZ_INTERP_NUM2  = 70                  # Number of interpolation points in Z
XZ_DPI          = 500                 # Output image resolution
XZ_X_MIN, XZ_X_MAX = 1, 100           # X-axis domain limits
XZ_Z_MIN, XZ_Z_MAX = 25, 165          # Z-axis domain limits
XZ_COLOR        = 'blue'              # Quiver arrow color
XZ_SCALE_FACTOR = 0.757               # Scaling factor applied to vector components

# Plot configuration for YZ plane
YZ_INTERP_NUM   = 50                  # Number of interpolation points in Y
YZ_INTERP_NUM2  = 70                  # Number of interpolation points in Z
YZ_DPI          = 500                 # Output image resolution
YZ_Y_MIN, YZ_Y_MAX = 1, 100           # Y-axis domain limits
YZ_Z_MIN, YZ_Z_MAX = 25, 165          # Z-axis domain limits
YZ_COLOR        = 'blue'              # Quiver arrow color
YZ_SCALE_FACTOR = 0.757               # Scaling factor applied to vector components

OUTPUT_EXT      = 'jpg'               # Image file extension for plots
PXYZ_FILENAME   = 'pxyz.in'           # Filename for full 3D data output
#################################################

################# SUMMARY CONFIG ##################
# Root directory for collected plots
SUMMARY_ROOT    = 'summary'
# Subdirectories for each plane
PLANE_DIRS = {
    'XY': os.path.join(SUMMARY_ROOT, 'XY'),
    'XZ': os.path.join(SUMMARY_ROOT, 'XZ'),
    'YZ': os.path.join(SUMMARY_ROOT, 'YZ'),
}
# CSV summary files for each plane (headers: task_id,parameters,filename)
PLANE_CSV = {
    'XY': os.path.join(PLANE_DIRS['XY'], 'XY_summary.csv'),
    'XZ': os.path.join(PLANE_DIRS['XZ'], 'XZ_summary.csv'),
    'YZ': os.path.join(PLANE_DIRS['YZ'], 'YZ_summary.csv'),
}
###################################################

def ensure_summary_setup():
    """
    Create summary directories and initialize CSV files with headers if not present.
    """
    os.makedirs(SUMMARY_ROOT, exist_ok=True)
    for plane, path in PLANE_DIRS.items():
        os.makedirs(path, exist_ok=True)
        csv_path = PLANE_CSV[plane]
        if not os.path.isfile(csv_path):
            with open(csv_path, 'w') as f:
                f.write('task_id,parameters,filename\n')


def parse_task_info(folder_name):
    """
    Extract task ID and parameter string from folder name.
    Assumes format: task_{id}_{param1}_{val1}_{param2}_{val2}_...
    Returns:
        task_id (str), parameters (str in 'name=value;...' format)
    """
    parts = folder_name.split('_')
    task_id = parts[1]
    params = parts[2:]
    pairs = []
    for i in range(0, len(params), 2):
        name = params[i]
        val = params[i+1] if i+1 < len(params) else ''
        pairs.append(f"{name}={val}")
    return task_id, ';'.join(pairs)


def summarize_plots(folder, folder_name):
    """
    Copy generated quiver plots to summary directories and append entries to CSVs.
    """
    task_id, param_str = parse_task_info(folder_name)
    for plane in ('XY', 'XZ', 'YZ'):
        src = os.path.join(folder, f"{plane}_quiver.{OUTPUT_EXT}")
        if os.path.isfile(src):
            dst_name = f"{folder_name}_{plane}.{OUTPUT_EXT}"
            dst = os.path.join(PLANE_DIRS[plane], dst_name)
            shutil.copy2(src, dst)
            with open(PLANE_CSV[plane], 'a') as f:
                f.write(f"{task_id},{param_str},{dst_name}\n")


def slice_data(folder):
    """
    Aggregate 3D data from multiple chunk files and write slice data.

    Steps:
      1. Read header from each PELOOP file to determine grid dimensions (nx, ny, nz).
      2. Initialize 3D arrays for px, py, pz if first chunk.
      3. Fill arrays using indices and values from each file.
      4. Optionally write full 3D dataset to PXYZ_FILENAME if WRITE_PXYZ is True.
      5. Compute 0-based slice indices from user config.
      6. Extract XY, XZ, YZ slices and write to respective .dat files.

    Parameters:
        folder (str): Path to the task directory containing chunk files.

    Returns:
        success (bool): True if all files processed and slices written; False on error.
    """
    pxx = pyy = pzz = None
    nx = ny = nz = None

    # Loop through each chunk file
    for chunk in range(NUM_CHUNKS):
        idx = TIME_STEP + chunk
        fname = DAT_PATTERN % idx
        fpath = os.path.join(folder, fname)

        # Check file existence
        if not os.path.isfile(fpath):
            print(f"Missing chunk: {fpath}")
            return False

        # Read data file
        with open(fpath) as f:
            header = f.readline().split()
            if len(header) < 3:
                print(f"Bad header in {fpath}")
                return False

            # Initialize arrays based on first header
            if pxx is None:
                nx, ny, nz = map(int, header[:3])
                pxx = np.zeros((nx, ny, nz))
                pyy = np.zeros((nx, ny, nz))
                pzz = np.zeros((nx, ny, nz))

            # Parse data lines into arrays
            for line in f:
                pts = line.split()
                if len(pts) < 6:
                    continue
                i1, j1, k1 = map(int, pts[:3])
                px, py, pz = map(float, pts[3:6])
                pxx[i1-1, j1-1, k1-1] = px
                pyy[i1-1, j1-1, k1-1] = py
                pzz[i1-1, j1-1, k1-1] = pz

    # Optionally write full 3D data
    if WRITE_PXYZ:
        out_all = os.path.join(folder, PXYZ_FILENAME)
        with open(out_all, 'w') as f:
            f.write(f"{nx} {ny} {nz}\n")
            for i in range(nx):
                for j in range(ny):
                    for k in range(nz):
                        f.write(f"{i+1} {j+1} {k+1} {pxx[i,j,k]:.5e} {pyy[i,j,k]:.5e} {pzz[i,j,k]:.5e}\n")

    # Compute slice indices (0-based)
    k_xy = XY_SLICE_K - 1
    j_xz = (XZ_J_INDEX - 1) if XZ_J_INDEX else (ny // 2)
    i_yz = (YZ_I_INDEX - 1) if YZ_I_INDEX else (nx // 2)

    # Write XY slice: columns i, j, px, py
    with open(os.path.join(folder, 'XY.dat'), 'w') as f:
        for i in range(nx):
            for j in range(ny):
                f.write(f"{i+1} {j+1} {pxx[i,j,k_xy]:.5e} {pyy[i,j,k_xy]:.5e}\n")

    # Write XZ slice: columns i, k, px, pz
    with open(os.path.join(folder, 'XZ.dat'), 'w') as f:
        for i in range(nx):
            for k in range(nz):
                f.write(f"{i+1} {k+1} {pxx[i,j_xz,k]:.5e} {pzz[i,j_xz,k]:.5e}\n")

    # Write YZ slice: columns j, k, py, pz
    with open(os.path.join(folder, 'YZ.dat'), 'w') as f:
        for j in range(ny):
            for k in range(nz):
                f.write(f"{j+1} {k+1} {pyy[i_yz,j,k]:.5e} {pzz[i_yz,j,k]:.5e}\n")

    return True


def plot_xy(folder):
    """
    Generate a quiver plot for the XY slice.
    """
    data = np.loadtxt(os.path.join(folder, 'XY.dat'))
    X, Y, PX, PY = data[:,0], data[:,1], data[:,2], data[:,3]

    # Create interpolation grid
    xx = np.linspace(XY_X_MIN, XY_X_MAX, XY_INTERP_NUM)
    yy = np.linspace(XY_Y_MIN, XY_Y_MAX, XY_INTERP_NUM2)
    xxg, yyg = np.meshgrid(xx, yy)

    # Interpolate vector components onto grid
    PXi = interpolate.griddata((X, Y), PX, (xxg, yyg), method='cubic')
    PYi = interpolate.griddata((X, Y), PY, (xxg, yyg), method='cubic')

    # Plot using quiver
    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.axis('off')
    ax.quiver(xxg, yyg, PXi, PYi,
              color=XY_COLOR, units='inches', angles='xy', pivot='mid', headwidth=3.8)
    plt.savefig(os.path.join(folder, f"XY_quiver.{OUTPUT_EXT}"), dpi=XY_DPI,
                bbox_inches='tight', pad_inches=0)
    plt.close(fig)


def plot_xz(folder):
    """
    Generate a quiver plot for the XZ slice.
    """
    data = np.loadtxt(os.path.join(folder, 'XZ.dat'))
    X, Z, PX, PZ = data[:,0], data[:,1], data[:,2] * XZ_SCALE_FACTOR, data[:,3] * XZ_SCALE_FACTOR

    # Create interpolation grid
    xx = np.linspace(XZ_X_MIN, XZ_X_MAX, XZ_INTERP_NUM)
    zz = np.linspace(XZ_Z_MIN, XZ_Z_MAX, XZ_INTERP_NUM2)
    xxg, zzg = np.meshgrid(xx, zz)

    # Interpolate vector components onto grid
    PXi = interpolate.griddata((X, Z), PX, (xxg, zzg), method='cubic')
    PZi = interpolate.griddata((X, Z), PZ, (xxg, zzg), method='cubic')

    # Plot using quiver
    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.axis('off')
    ax.quiver(xxg, zzg, PXi, PZi,
              color=XZ_COLOR, units='inches', angles='xy', pivot='mid', headwidth=3.8)
    plt.savefig(os.path.join(folder, f"XZ_quiver.{OUTPUT_EXT}"), dpi=XZ_DPI,
                bbox_inches='tight', pad_inches=0)
    plt.close(fig)


def plot_yz(folder):
    """
    Generate a quiver plot for the YZ slice.
    """
    data = np.loadtxt(os.path.join(folder, 'YZ.dat'))
    Y, Z, PY, PZ = data[:,0], data[:,1], data[:,2] * YZ_SCALE_FACTOR, data[:,3] * YZ_SCALE_FACTOR

    # Create interpolation grid
    yy = np.linspace(YZ_Y_MIN, YZ_Y_MAX, YZ_INTERP_NUM)
    zz = np.linspace(YZ_Z_MIN, YZ_Z_MAX, YZ_INTERP_NUM2)
    yyg, zzg = np.meshgrid(yy, zz)

    # Interpolate vector components onto grid
    PYi = interpolate.griddata((Y, Z), PY, (yyg, zzg), method='cubic')
    PZi = interpolate.griddata((Y, Z), PZ, (yyg, zzg), method='cubic')

    # Plot using quiver
    fig, ax = plt.subplots()
    ax.set_aspect('equal')
    ax.axis('off')
    ax.quiver(yyg, zzg, PYi, PZi,
              color=YZ_COLOR, units='inches', angles='xy', pivot='mid', headwidth=3.8)
    plt.savefig(os.path.join(folder, f"YZ_quiver.{OUTPUT_EXT}"), dpi=YZ_DPI,
                bbox_inches='tight', pad_inches=0)
    plt.close(fig)


def main():
    """
    Main batch workflow:
      1. Setup summary directories and CSVs.
      2. Discover task directories under BASE_DIR.
      3. For each, call slice_data, plotting, and summarization.
      4. Report completion.
    """
    ensure_summary_setup()
    tasks = sorted(d for d in os.listdir(BASE_DIR)
                   if os.path.isdir(os.path.join(BASE_DIR, d)))
    for t in tasks:
        folder = os.path.join(BASE_DIR, t)
        print(f"Processing {t}, time step {TIME_STEP}...")

        # Slice and write data; skip if failure
        if not slice_data(folder):
            continue

        # Generate quiver plots for each plane
        plot_xy(folder)
        plot_xz(folder)
        plot_yz(folder)

        # Summarize plots: copy to summary and record
        summarize_plots(folder, t)

    print("Batch processing completed.")

if __name__ == '__main__':
    main()
