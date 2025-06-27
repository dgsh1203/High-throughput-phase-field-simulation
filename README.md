# High-Throughput Phase-Field Simulation Toolkit

A toolkit for automating large parameter sweeps of phase-field simulations with SLURM submission, plus batch post-processing to extract 2D slices and generate quiver-plot visualizations.

---

## Table of Contents

1. [Overview](#overview)  
2. [Prerequisites](#prerequisites)  
3. [Directory Structure](#directory-structure)  
4. [Setup](#setup)  
5. [Parameter Sweep Script](#parameter-sweep-script)  
6. [Data Processing Script](#data-processing-script)  
7. [Configuration Options](#configuration-options)  
8. [Notes & Tips](#notes--tips)  
9. [License](#license)  

---

## Overview

- **Script 1:** `sweep.py` — interactively defines parameter ranges, generates combinations, applies symmetry filtering, creates per-task folders from a template, writes input files, and optionally submits jobs to SLURM.  
- **Script 2:** `process.py` — traverses all task folders, aggregates 3D polar data, extracts mid-plane or specified 2D slices, interpolates the field, and produces high-resolution quiver plots. Summaries and CSV indices are collected under `summary/`.

---

## Prerequisites

- Linux or macOS environment  
- Python 3.8+  
- [NumPy](https://numpy.org/)  
- [SciPy](https://scipy.org/)  
- [Matplotlib](https://matplotlib.org/)  
- SLURM (for job submission)  
- A working phase-field simulation package (provided in `phasefield_pkg/`)

Install Python deps via:
```bash
pip install numpy scipy matplotlib
Directory Structure
Place all items at the same level:

.
├── phasefield_pkg/       ← your simulation software package
├── sweep.py             ← parameter sweep & submission script
├── process.py           ← batch data-processing & plotting script
└── origin/              ← template folder (contains inputN.in, V-3.sh, Makefile, etc.)
After first run you’ll get:

├── tasks/               ← auto-generated per-task folders (task_1_…)
│   ├── task_1_…/
│   └── task_2_…/
└── summary/             ← aggregated outputs
    ├── XY/, XZ/, YZ/
    └── XY_summary.csv, XZ_summary.csv, YZ_summary.csv
Setup
Place everything at the same directory level (see above).

Edit phasefield_pkg/Makefile and origin/V-3.sh to match your system paths, compiler flags, and SLURM directives.

Compile your simulation code:

cd phasefield_pkg
make clean && make all
cd ..
Verify that running your simulation executable from within origin/ produces expected output files.

Parameter Sweep Script
Run:

python3 sweep.py
Template discovery: ensures origin/ and origin/inputN.in exist.

Parameter parsing: reads commented fields in inputN.in marked with ! param1, param2, ....

Interactive prompts:

Select how many parameters to scan

Choose each by name or index

Enter start, end, and step values

Combination preview (first 5 sets) and total-count confirmation.

Symmetry filter: if both asub1 and asub2 are scanned, only keeps combinations with asub1 ≤ asub2.

Directory creation: creates tasks/task_<id>_<param>_<value>… for each combo.

Input file writing: writes updated inputN.in in each folder.

Metadata: writes tasks.csv listing each task’s folder and parameter values.

Optional SLURM submission: when confirmed, calls sbatch V-3.sh inside each task folder.

Data Processing Script
Run:

python3 process.py
Initialize summary directories (summary/XY, summary/XZ, summary/YZ) and CSV headers.

Discover all tasks/task_* folders.

For each task:

Read and aggregate chunked 3D data (PELOOP.%08d.dat).

Slice into 2D planes (XY, XZ, YZ), with mid-plane default if no index provided.

Interpolate onto a uniform grid.

Plot quiver diagrams at high DPI and save as XY_quiver.jpg, XZ_quiver.jpg, YZ_quiver.jpg.

Summarize by copying plots into summary/<plane>/ and appending entries to <plane>_summary.csv.

Completion message when all tasks processed.

Configuration Options
All configurable parameters are defined at the top of each script:

In sweep.py
template (folder name)

input_file (filename in template)

In process.py

BASE_DIR        = 'tasks'
TIME_STEP       = 500
NUM_CHUNKS      = 20
DAT_PATTERN     = 'PELOOP.%08d.dat'
WRITE_PXYZ      = False

# Slice indices (1-based; None = mid-plane)
XY_SLICE_K      = 150
XZ_J_INDEX      = None
YZ_I_INDEX      = None

# Interpolation/grid & plot settings per plane
XY_INTERP_NUM   = 50
XY_INTERP_NUM2  = 50
XY_DPI          = 500
XY_X_MIN, XY_X_MAX = 1, 100
XY_Y_MIN, XY_Y_MAX = 1, 100

# [Similarly for XZ and YZ planes…]
Adjust these values before running to fit your domain size, resolution needs, and desired image quality.

Notes & Tips
Template edits: keep a pristine copy of origin/ in version control; only modify Makefile and SLURM script (V-3.sh).

Error handling: missing data chunks or bad headers are reported and skipped. Inspect console output for failed tasks.

Scaling factors: in process.py, XZ_SCALE_FACTOR and YZ_SCALE_FACTOR uniformly scale vector lengths for visual clarity.

Output formats: change OUTPUT_EXT (e.g. to png) if desired.

Extending: you can wrap these scripts into a higher-level workflow manager or integrate with other HPC schedulers by swapping out the SLURM submission call.

