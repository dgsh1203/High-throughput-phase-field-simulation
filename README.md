# High-Throughput Phase-Field Simulation Toolkit

Automates large-scale parameter sweeps and batch post-processing of polar field data, producing 2D quiver-plot visualizations.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Directory Structure](#directory-structure)
3. [Installation & Compilation](#installation--compilation)
4. [Quick Start](#quick-start)
5. [Detailed Usage](#detailed-usage)

   1. [1. Parameter Sweep Script](#1-parameter-sweep-script)
   2. [2. Batch Data Processing Script](#2-batch-data-processing-script)
6. [Configuration Notes](#configuration-notes)
7. [Output & Results](#output--results)
8. [License](#license)

---

## Prerequisites

* **Operating System:** Linux / macOS
* **Tools & Libraries:**

  * Python 3.8+
  * NumPy
  * SciPy
  * Matplotlib
  * GNU Make
  * SLURM (for optional job submission)
* **Hardware:**

  * Multi-core CPU (recommended)
  * Sufficient disk space for simulation outputs

---

## Directory Structure

```
your_project_root/
├── phasefield_package/       ← Compiled simulation software  
│   ├── Makefile  
│   ├── V-3.sh                ← SLURM job script template  
│   └── ...                   ← Other executables & resources  
├── sweep.py                  ← High-throughput parameter sweep script  
├── process.py                ← Batch data-processing & plotting script  
└── origin/                   ← Template input directory  
    └── inputN.in             ← Example template input file  
```

---

## Installation & Compilation

1. **Clone or copy** the entire project directory to your local machine.
2. **Enter** the simulation package folder:

   ```bash
   cd phasefield_package
   ```
3. **Edit** `Makefile` and `V-3.sh` to match your system’s compiler, library paths, and SLURM settings.
4. **Compile** the phase-field binary:

   ```bash
   make
   ```

   On success, an executable (e.g., `phasefield_exec`) will be generated in this folder.

---

## Quick Start

1. Ensure **all three** items are in the same directory level:

   * `phasefield_package/`
   * `sweep.py`
   * `process.py`
2. **Generate & (optionally) submit** a batch of simulation tasks:

   ```bash
   python3 sweep.py
   ```
3. **Process & visualize** results after simulations finish:

   ```bash
   python3 process.py
   ```

---

## Detailed Usage

### 1. Parameter Sweep Script

**File:** `sweep.py`

1. **Template directory:**

   * `origin/` must contain `inputN.in`, the template with commented “! parameter\_name” fields.
2. **Run:**

   ```bash
   python3 sweep.py
   ```
3. **Interactive prompts:**

   1. Select which parameters to scan.
   2. Input **start**, **end**, and **step** values.
   3. Preview combinations (first 5 sets).
   4. Confirm creation and SLURM submission.
4. **Outputs:**

   * `tasks/` folder with subfolders `task_1_<params>/`, …
   * `tasks.csv` listing task IDs, folder names, and parameter values.

### 2. Batch Data Processing Script

**File:** `process.py`

1. **Configuration** at top of script:

   * `BASE_DIR`: root of `tasks/`
   * Time-step & chunk settings (`TIME_STEP`, `NUM_CHUNKS`, `DAT_PATTERN`)
   * Slice indices (`XY_SLICE_K`, etc.)
   * Plot settings (`*_INTERP_NUM`, DPI, domain limits)
2. **Run:**

   ```bash
   python3 process.py
   ```
3. **Workflow:**

   1. Creates `summary/XY`, `summary/XZ`, `summary/YZ` directories.
   2. Iterates each `task_*` folder:

      * Aggregates 3D data, extracts XY/XZ/YZ slices.
      * Generates quiver plots (`XY_quiver.jpg`, etc.).
      * Copies plots to `summary/<plane>/` and appends entries to `<plane>_summary.csv`.
4. **Outputs:**

   * `summary/` with plots and CSV summaries per plane.

---

## Configuration Notes

* **Folder placement:** `phasefield_package/`, `sweep.py`, and `process.py` **must** reside at the same hierarchy level.
* **Makefile & V-3.sh:**

  * Update compiler flags, include paths, and SLURM directives (`#SBATCH`) to match your cluster.
* **Python dependencies:**

  ```bash
  pip3 install numpy scipy matplotlib
  ```
* **SLURM submission:**

  * If you choose **not** to submit jobs automatically, answer **“n”** when prompted during `sweep.py`.

---

## Output & Results

* **Task folders:**

  ```
  tasks/
  ├── task_1_asub1_3_asub2_3/
  │   ├── inputN.in
  │   ├── PELOOP.00500.dat …
  │   └── XY_quiver.jpg …
  └── …
  ```
* **Summary plots & CSVs:**

  ```
  summary/
  ├── XY/
  │   ├── task_1_asub1_3_asub2_3_XY.jpg
  │   └── XY_summary.csv
  ├── XZ/ …
  └── YZ/ …
  ```

---

## License

This toolkit is released under the MIT License. See [LICENSE](LICENSE) for details.
