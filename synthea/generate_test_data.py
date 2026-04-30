#!/usr/bin/env python3
"""
Generate synthetic FHIR test data using Synthea custom modules.

This script automates running Synthea with PheKB-based modules to generate
test data for FHIR query evaluation.

Usage:
    python generate_test_data.py --phenotype type-2-diabetes --patients 20
    python generate_test_data.py --phenotype type-2-diabetes --patients 20 --controls 20
    python generate_test_data.py --list-modules
"""

import argparse
import glob as glob_module
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Paths
SCRIPT_DIR = Path(__file__).parent
MODULES_DIR = SCRIPT_DIR / "modules" / "custom"
OUTPUT_DIR = SCRIPT_DIR / "output"

# Synthea installation directory - configurable via SYNTHEA_HOME env var
SYNTHEA_HOME = Path(os.environ.get("SYNTHEA_HOME", r"C:\repos\synthea"))

# Common Java install locations on Windows
_JAVA_SEARCH_PATHS = [
    r"C:\Program Files\Eclipse Adoptium",
    r"C:\Program Files\Java",
    r"C:\Program Files\Microsoft\jdk-*",
    r"C:\Program Files\Zulu",
    r"C:\Program Files\Amazon Corretto",
]


def _find_java_home() -> Optional[str]:
    """Auto-detect JAVA_HOME from common Windows install locations."""
    # Already set?
    java_home = os.environ.get("JAVA_HOME")
    if java_home and Path(java_home).exists():
        return java_home

    # java already on PATH?
    if shutil.which("java"):
        return None  # No need to set JAVA_HOME

    # Search common locations
    for pattern in _JAVA_SEARCH_PATHS:
        for base in glob_module.glob(pattern):
            base_path = Path(base)
            # Check for direct jdk dirs or nested ones
            if (base_path / "bin" / "java.exe").exists():
                return str(base_path)
            # Check subdirectories (e.g., C:\Program Files\Eclipse Adoptium\jdk-17.x.x)
            for sub in sorted(base_path.iterdir(), reverse=True):
                if sub.is_dir() and (sub / "bin" / "java.exe").exists():
                    return str(sub)
    return None


def _ensure_java_env() -> None:
    """Ensure JAVA_HOME is set and java is on PATH."""
    if shutil.which("java"):
        return

    java_home = _find_java_home()
    if java_home:
        os.environ["JAVA_HOME"] = java_home
        java_bin = str(Path(java_home) / "bin")
        os.environ["PATH"] = java_bin + os.pathsep + os.environ.get("PATH", "")
        print(f"Auto-detected JAVA_HOME: {java_home}")
    else:
        print("WARNING: Could not find Java. Ensure Java 11+ is installed.")
        print("  Set JAVA_HOME or add java to PATH.")


def _is_bash_environment() -> bool:
    """Detect if running inside a bash-like shell (git bash, WSL, etc.)."""
    shell = os.environ.get("SHELL", "")
    if "/bash" in shell or "/zsh" in shell:
        return True
    # Check for MSYSTEM (git bash sets this)
    if os.environ.get("MSYSTEM"):
        return True
    return False


def _to_forward_slashes(path: str) -> str:
    """Convert Windows backslashes to forward slashes for Gradle compatibility."""
    return path.replace("\\", "/")


def _get_gradlew() -> Path:
    """Get the Gradle wrapper script path.

    On Windows, always use gradlew.bat because Python's subprocess.run
    uses CreateProcess which can't execute Unix shell scripts, even when
    running inside git bash.
    """
    if sys.platform == "win32":
        return SYNTHEA_HOME / "gradlew.bat"
    return SYNTHEA_HOME / "gradlew"


def _get_synthea_cmd() -> Path:
    """Get the platform-appropriate Synthea run script."""
    if sys.platform == "win32":
        return SYNTHEA_HOME / "run_synthea.bat"
    return SYNTHEA_HOME / "run_synthea"


def list_available_modules() -> list[str]:
    """List available custom modules."""
    modules = []
    if MODULES_DIR.exists():
        for f in MODULES_DIR.glob("phekb_*.json"):
            # Skip control modules in the list
            if "_control" not in f.stem:
                # Convert filename to phenotype name
                name = f.stem.replace("phekb_", "").replace("_", "-")
                modules.append(name)
    return sorted(set(modules))


def get_module_info(phenotype: str) -> dict:
    """Get information about a module."""
    module_file = MODULES_DIR / f"phekb_{phenotype.replace('-', '_')}.json"
    if not module_file.exists():
        return {}

    with open(module_file) as f:
        data = json.load(f)

    return {
        "name": data.get("name", ""),
        "remarks": data.get("remarks", []),
        "file": str(module_file)
    }


def run_synthea(
    module_name: str,
    num_patients: int,
    output_subdir: str,
    seed: Optional[int] = None
) -> bool:
    """
    Run Synthea with a custom module.

    Uses ./gradlew directly when running in a bash environment (git bash, WSL)
    to avoid issues with .bat files not executing natively in bash.
    All paths are converted to forward slashes for Gradle compatibility.

    Args:
        module_name: Name of the module (without .json extension)
        num_patients: Number of patients to generate
        output_subdir: Subdirectory for output
        seed: Random seed for reproducibility

    Returns:
        True if successful, False otherwise
    """
    _ensure_java_env()

    gradlew = _get_gradlew()
    if not gradlew.exists():
        print(f"ERROR: Synthea not found at {SYNTHEA_HOME}")
        print(f"Expected gradle wrapper: {gradlew}")
        print()
        print("Set SYNTHEA_HOME environment variable to your Synthea installation,")
        print("or clone Synthea: git clone https://github.com/synthetichealth/synthea.git")
        return False

    output_path = (OUTPUT_DIR / output_subdir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # Use absolute paths with forward slashes for Gradle compatibility
    modules_dir_str = _to_forward_slashes(str(MODULES_DIR.resolve()))
    output_path_str = _to_forward_slashes(str(output_path))

    use_bash = _is_bash_environment()

    if use_bash:
        # In bash: call ./gradlew directly with -Params
        # Single-quote each arg for Gradle's Groovy parser
        params_parts = [
            f"'-p'",
            f"'{num_patients}'",
            f"'-m'",
            f"'{module_name}'",
            f"'-d'",
            f"'{modules_dir_str}'",
            f"'--exporter.fhir.export'",
            f"'true'",
            f"'--exporter.fhir.use_us_core_ig'",
            f"'true'",
            f"'--exporter.baseDirectory'",
            f"'{output_path_str}'",
        ]
        if seed is not None:
            params_parts.extend([f"'-s'", f"'{seed}'"])

        params_str = ",".join(params_parts)
        cmd = [str(gradlew), "run", f'-Params=[{params_str}]']
    else:
        # Native Windows cmd.exe: use run_synthea.bat as before
        synthea_cmd = _get_synthea_cmd()
        cmd = [
            str(synthea_cmd),
            "-p", str(num_patients),
            "-m", module_name,
            "-d", modules_dir_str,
            "--exporter.fhir.export=true",
            "--exporter.fhir.use_us_core_ig=true",
            f"--exporter.baseDirectory={output_path_str}",
        ]
        if seed is not None:
            cmd.extend(["-s", str(seed)])

    print(f"Environment: {'bash' if use_bash else 'cmd.exe'}")
    print(f"Running: {' '.join(cmd)}")
    print(f"Synthea home: {SYNTHEA_HOME}")
    print(f"Custom modules: {modules_dir_str}")
    print(f"Output directory: {output_path_str}")
    print()

    try:
        result = subprocess.run(cmd, check=True, cwd=str(SYNTHEA_HOME))
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Synthea failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print("ERROR: Could not run Synthea. Ensure Java 11+ is installed")
        print(f"  and Synthea exists at: {SYNTHEA_HOME}")
        return False


def generate_phenotype_data(
    phenotype: str,
    num_positive: int = 20,
    num_control: int = 20,
    seed: Optional[int] = None
) -> bool:
    """
    Generate both positive and control cases for a phenotype.

    Args:
        phenotype: Phenotype name (e.g., "type-2-diabetes")
        num_positive: Number of positive cases
        num_control: Number of control cases
        seed: Random seed for reproducibility

    Returns:
        True if successful, False otherwise
    """
    module_base = f"phekb_{phenotype.replace('-', '_')}"

    # Check modules exist
    positive_module = MODULES_DIR / f"{module_base}.json"
    control_module = MODULES_DIR / f"{module_base}_control.json"

    if not positive_module.exists():
        print(f"ERROR: Module not found: {positive_module}")
        return False

    success = True

    # Generate positive cases
    print(f"=== Generating {num_positive} positive cases for {phenotype} ===")
    if not run_synthea(module_base, num_positive, f"{phenotype}/positive", seed):
        success = False

    # Generate control cases if module exists
    if control_module.exists() and num_control > 0:
        print()
        print(f"=== Generating {num_control} control cases for {phenotype} ===")
        control_seed = seed + 1000 if seed else None
        if not run_synthea(f"{module_base}_control", num_control, f"{phenotype}/control", control_seed):
            success = False
    elif num_control > 0:
        print(f"WARNING: Control module not found: {control_module}")

    return success


def count_generated_patients(phenotype: str) -> dict:
    """Count generated patients in output directory."""
    counts = {"positive": 0, "control": 0}

    positive_dir = OUTPUT_DIR / phenotype / "positive" / "fhir"
    control_dir = OUTPUT_DIR / phenotype / "control" / "fhir"

    if positive_dir.exists():
        counts["positive"] = len(list(positive_dir.glob("*.json")))

    if control_dir.exists():
        counts["control"] = len(list(control_dir.glob("*.json")))

    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic FHIR test data using Synthea"
    )
    parser.add_argument(
        "--phenotype", "-p",
        help="Phenotype to generate (e.g., type-2-diabetes)"
    )
    parser.add_argument(
        "--patients", "-n",
        type=int,
        default=20,
        help="Number of positive patients to generate (default: 20)"
    )
    parser.add_argument(
        "--controls", "-c",
        type=int,
        default=20,
        help="Number of control patients to generate (default: 20)"
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--list-modules", "-l",
        action="store_true",
        help="List available phenotype modules"
    )
    parser.add_argument(
        "--info", "-i",
        help="Show info about a specific module"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show status of generated data"
    )

    args = parser.parse_args()

    if args.list_modules:
        modules = list_available_modules()
        if modules:
            print("Available phenotype modules:")
            for m in modules:
                print(f"  - {m}")
        else:
            print("No custom modules found in:", MODULES_DIR)
        return 0

    if args.info:
        info = get_module_info(args.info)
        if info:
            print(f"Module: {info['name']}")
            print(f"File: {info['file']}")
            print("Description:")
            for remark in info['remarks']:
                if remark:
                    print(f"  {remark}")
        else:
            print(f"Module not found: {args.info}")
            return 1
        return 0

    if args.status:
        modules = list_available_modules()
        print("Generated data status:")
        print("-" * 50)
        for m in modules:
            counts = count_generated_patients(m)
            total = counts['positive'] + counts['control']
            if total > 0:
                print(f"  {m}: {counts['positive']} positive, {counts['control']} control")
            else:
                print(f"  {m}: (no data generated)")
        return 0

    if not args.phenotype:
        parser.print_help()
        print("\nAvailable phenotypes:", ", ".join(list_available_modules()))
        return 1

    # Check Synthea installation exists
    synthea_cmd = _get_synthea_cmd()
    if not synthea_cmd.exists():
        print(f"ERROR: Synthea not found at {SYNTHEA_HOME}")
        print()
        print("Set SYNTHEA_HOME environment variable to your Synthea installation, or:")
        print("  git clone https://github.com/synthetichealth/synthea.git C:\\repos\\synthea")
        return 1

    success = generate_phenotype_data(
        args.phenotype,
        args.patients,
        args.controls,
        args.seed
    )

    if success:
        counts = count_generated_patients(args.phenotype)
        print()
        print("=" * 50)
        print(f"Generated {counts['positive']} positive and {counts['control']} control patients")
        print(f"Output: {OUTPUT_DIR / args.phenotype}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
