#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive high-throughput parameter sweep control script with symmetry filtering for asub1/asub2.

Written by Guanshihan Du on 2025-06-25

This script automates the creation and optional submission of multiple simulation tasks
by sweeping over user-defined ranges of input parameters. It parses adjustable parameters
from commented fields in a template input file, prompts the user to define scan ranges,
previews combinations, applies symmetry filtering for asub1 and asub2 to avoid redundant
ferroelectric film simulations when lattice parameters are swapped, and then generates
task directories with updated input files, records metadata, and optionally submits jobs
via SLURM.
"""
import os
import shutil
import itertools
import csv


def parse_input_file(input_path):
    """
    Read the template input file and identify adjustable parameters.

    Parameters:
        input_path (str): Path to the template input file.

    Returns:
        lines (list of str): All lines from the file.
        param_map (dict): Mapping from parameter name to a tuple
                          (line_index, field_index) indicating where in
                          the file the value for that parameter resides.
    """
    with open(input_path, 'r') as f:
        lines = f.readlines()

    param_map = {}
    # Iterate over each line to find comments marking adjustable parameters
    for idx, line in enumerate(lines):
        # Look for a '!' character followed by comma-separated names
        if '!' in line and ',' in line.split('!')[1]:
            # Extract the comment portion after '!'
            comment = line.split('!')[1].split('(')[0]
            # Split by comma to get individual parameter names
            names = [n.strip().strip(',') for n in comment.split(',') if n.strip()]
            # Extract the part before '!' and split into fields (values)
            values = line.split('!')[0].split()
            # Map each name to its position in the line
            for pos, name in enumerate(names):
                if pos < len(values):
                    param_map[name] = (idx, pos)
    return lines, param_map


def generate_param_combinations(scan_specs):
    """
    Generate all parameter combinations based on user-defined scan specifications.

    Parameters:
        scan_specs (list of tuples): Each tuple is (name, start, end, step).

    Returns:
        names (list of str): Ordered list of parameter names.
        combos (list of tuples): Cartesian product of all parameter values.
    """
    names = []       # Parameter names in scan order
    lists = []       # Lists of values for each parameter

    for name, start, end, step in scan_specs:
        names.append(name)
        vals = []
        # Determine integer versus floating-point ranges
        if all(isinstance(v, int) for v in (start, end, step)):
            # Inclusive range for integers
            vals = list(range(start, end + (1 if step > 0 else -1), step))
        else:
            # Floating-point range: accumulate until <= end (with tolerance)
            v = start
            while v <= end + 1e-12:
                vals.append(round(v, 12))
                v += step
        lists.append(vals)

    # Compute Cartesian product of all value lists
    combos = list(itertools.product(*lists))
    return names, combos


def modify_input(lines, param_map, combo, param_names):
    """
    Create a modified copy of the template lines with one set of parameter values applied.

    Parameters:
        lines (list of str): Original template file lines.
        param_map (dict): Mapping of parameter names to (line_index, field_index).
        combo (tuple): Specific combination of values for each parameter.
        param_names (list): Names of parameters in the same order as combo.

    Returns:
        new (list of str): Updated lines with values replaced.
    """
    # Copy lines to avoid mutating the original
    new = lines.copy()
    # For each parameter, replace the numeric field at its location
    for name, val in zip(param_names, combo):
        ln, pos = param_map[name]
        # Split the line at the comment marker (if exists)
        before, *rest = new[ln].split('!')
        nums = before.split()  # Numeric fields before the comment
        nums[pos] = str(val)   # Set the new value
        # Reattach any trailing comment
        comment = '!' + rest[0] if rest else ''
        new[ln] = ' '.join(nums) + ' ' + comment
    return new


def sanitize(val):
    """
    Convert a numeric value to a string safe for filenames.

    Parameters:
        val (int or float): The parameter value.

    Returns:
        s (str): Filename-safe representation (preserves sign and decimal).
    """
    return str(val)


def main():
    """
    Main workflow:
      1. Verify the template directory and input file exist.
      2. Parse adjustable parameters from the template file.
      3. Prompt the user to select parameters and define scan ranges.
      4. Generate all combinations, apply symmetry filtering for asub1/asub2.
      5. Preview, confirm, create task directories, write inputs, record metadata.
      6. Optionally submit each task via SLURM.
    """
    template = 'origin'
    input_file = 'inputN.in'

    # Check for the template directory
    if not os.path.isdir(template):
        print(f"Error: template '{template}' not found.")
        return

    # Build full path to the template input file and parse
    template_input = os.path.join(template, input_file)
    lines, param_map = parse_input_file(template_input)

    # Display available adjustable parameters
    params = sorted(param_map.keys())
    print("Available adjustable parameters:")
    for i, name in enumerate(params, start=1):
        print(f"  {i}. {name}")

    # Ask number of parameters to scan
    try:
        n = int(input("\nHow many parameters would you like to scan? "))
    except ValueError:
        print("Invalid number.")
        return

    scan_specs = []
    for idx in range(1, n+1):
        choice = input(f"Select parameter {idx} by number or name: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(params):
            name = params[int(choice)-1]
        elif choice in param_map:
            name = choice
        else:
            print(f"Invalid parameter '{choice}'.")
            return
        start = input(f"Enter start value for '{name}': ").strip()
        end   = input(f"Enter end   value for '{name}': ").strip()
        step  = input(f"Enter step  value for '{name}': ").strip()
        def to_num(s): return int(s) if s.isdigit() else float(s)
        try:
            s_val, e_val, st_val = to_num(start), to_num(end), to_num(step)
        except ValueError:
            print("Invalid numeric input.")
            return
        scan_specs.append((name, s_val, e_val, st_val))

    # Generate combinations
    param_names, combos = generate_param_combinations(scan_specs)

    # Symmetry filter: only keep combinations where asub1 <= asub2
    if 'asub1' in param_names and 'asub2' in param_names:
        i1 = param_names.index('asub1')
        i2 = param_names.index('asub2')
        original = len(combos)
        combos = [c for c in combos if c[i1] <= c[i2]]
        print(f"Applied symmetry filter: {original} -> {len(combos)} combinations.")

    total = len(combos)
    print(f"\nPlanning {total} tasks for parameters: {param_names}")

    # Preview first few sets
    preview_count = min(5, total)
    print("First few parameter sets:")
    for combo in combos[:preview_count]:
        print(dict(zip(param_names, combo)))

    confirm = input(f"Proceed to create and submit {total} tasks? [y/N] ").strip().lower()
    if confirm != 'y':
        print("Aborted by user.")
        return

    submit = input("Submit jobs via SLURM? [Y/n] ").strip().lower() != 'n'

    # Prepare output directory and CSV
    os.makedirs('tasks', exist_ok=True)
    csv_file = 'tasks.csv'
    with open(csv_file, 'w', newline='') as csvf:
        writer = csv.writer(csvf)
        writer.writerow(['id', 'folder'] + param_names)

        for idx, combo in enumerate(combos, 1):
            # Build descriptive folder name
            spec_parts = [f"{n}_{sanitize(v)}" for n, v in zip(param_names, combo)]
            folder_name = f"task_{idx}_{'_'.join(spec_parts)}"
            folder = os.path.join('tasks', folder_name)

            # Copy template and update input
            if os.path.exists(folder):
                shutil.rmtree(folder)
            shutil.copytree(template, folder)

            new_lines = modify_input(lines, param_map, combo, param_names)
            with open(os.path.join(folder, input_file), 'w') as f:
                f.writelines(new_lines)

            # Write metadata
            writer.writerow([idx, folder_name] + list(combo))

            # Optional SLURM submission
            if submit:
                os.system(f"cd {folder} && sbatch V-3.sh && cd ..")

    print(f"Completed {'submission' if submit else 'preparation'} of {total} tasks. Metadata in {csv_file}.")


if __name__ == '__main__':
    main()
