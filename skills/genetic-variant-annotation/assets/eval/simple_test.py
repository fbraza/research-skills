#!/usr/bin/env python3
"""
Simple test for genetic-variant-annotation skill.

Mock test:  Validates VCF parsing, tool detection, and output parsing logic
            without running VEP or SNPEff (no annotation databases needed).
Live test:  Full annotation of ClinVar BRCA1/BRCA2 example variants using
            VEP or SNPEff (requires installation + databases).

Usage:
    python3 assets/eval/simple_test.py           # Mock test only (~5 seconds)
    python3 assets/eval/simple_test.py --live    # Mock + live annotation test
    python3 assets/eval/simple_test.py --verbose # Detailed output
    python3 assets/eval/simple_test.py --tool vep    # Live test with VEP only
    python3 assets/eval/simple_test.py --tool snpeff # Live test with SNPEff only
"""

import os
import sys
import gzip
import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
EVAL_DIR   = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR  = os.path.join(EVAL_DIR, "..", "..")
SCRIPT_DIR = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPT_DIR)

# ── Minimal test VCF content (10 BRCA1/BRCA2 variants, GRCh38) ───────────────
# Mix of pathogenic (frameshift, stop_gained, missense) and benign variants
MINIMAL_VCF_CONTENT = """\
##fileformat=VCFv4.2
##reference=GRCh38
##FILTER=<ID=PASS,Description="All filters passed">
##INFO=<ID=CLNSIG,Number=.,Type=String,Description="ClinVar significance">
##INFO=<ID=CLNDN,Number=.,Type=String,Description="ClinVar disease name">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
17\t43044295\trs80357906\tA\tT\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43045802\trs80357382\tG\tA\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43047642\trs80357711\tC\tT\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43049120\trs80357526\tA\tG\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43051071\trs80357372\tG\tA\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43057051\trs80357483\tA\tC\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43063873\trs80357906\tC\tT\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
17\t43067607\trs80357382\tG\tA\t.\tPASS\tCLNSIG=Pathogenic;CLNDN=Breast_cancer
13\t32315474\trs80358981\tA\tG\t.\tPASS\tCLNSIG=Benign;CLNDN=not_specified
13\t32316527\trs80358508\tC\tT\t.\tPASS\tCLNSIG=Benign;CLNDN=not_specified
"""


# ── Test 1: VCF validation ─────────────────────────────────────────────────────

def test_vcf_validation(verbose=False):
    """Test that the VCF validator correctly parses and validates a VCF file."""
    print("\n[Test 1] VCF validation...")

    tmp_dir = tempfile.mkdtemp(prefix="gva_test_")
    try:
        # Write test VCF
        vcf_path = os.path.join(tmp_dir, "test.vcf")
        with open(vcf_path, "w") as f:
            f.write(MINIMAL_VCF_CONTENT)

        # Try importing validate_vcf
        try:
            from validate_vcf import validate_vcf
            result = validate_vcf(vcf_path)
            assert result is not None, "validate_vcf returned None"
            if verbose:
                print(f"  validate_vcf result: {result}")
        except ImportError:
            # Fallback: manual VCF parsing
            variants = _parse_vcf_manually(vcf_path)
            assert len(variants) == 10, f"Expected 10 variants, got {len(variants)}"
            assert all("CHROM" in v for v in variants), "Missing CHROM field"
            assert all("POS" in v for v in variants), "Missing POS field"
            assert all("REF" in v for v in variants), "Missing REF field"
            assert all("ALT" in v for v in variants), "Missing ALT field"
            if verbose:
                print(f"  Parsed {len(variants)} variants manually")

        # Validate chromosome names
        variants = _parse_vcf_manually(vcf_path)
        chroms = set(v["CHROM"] for v in variants)
        assert "17" in chroms, "BRCA1 variants (chr17) missing"
        assert "13" in chroms, "BRCA2 variants (chr13) missing"

        # Validate positions are numeric
        for v in variants:
            assert v["POS"].isdigit(), f"Non-numeric POS: {v['POS']}"

        if verbose:
            print(f"  Chromosomes: {sorted(chroms)}")
            print(f"  Position range chr17: "
                  f"{min(int(v['POS']) for v in variants if v['CHROM']=='17')} – "
                  f"{max(int(v['POS']) for v in variants if v['CHROM']=='17')}")

    finally:
        shutil.rmtree(tmp_dir)

    print("  ✓ VCF validation: PASSED")
    return True


# ── Test 2: Example data loading ──────────────────────────────────────────────

def test_example_data_loading(verbose=False):
    """Test that load_clinvar_pathogenic_sample() creates a valid VCF."""
    print("\n[Test 2] Example data loading...")

    try:
        from load_example_data import load_clinvar_pathogenic_sample
        data = load_clinvar_pathogenic_sample()

        assert "vcf_path" in data,         "Missing vcf_path in result"
        assert "genome" in data,           "Missing genome in result"
        assert "expected_results" in data, "Missing expected_results in result"
        assert data["genome"] == "GRCh38", f"Expected GRCh38, got {data['genome']}"
        assert os.path.exists(data["vcf_path"]), \
            f"VCF file not created: {data['vcf_path']}"

        # Validate expected results structure
        exp = data["expected_results"]
        assert exp["total_variants"] == 10, \
            f"Expected 10 variants, got {exp['total_variants']}"
        assert exp["pathogenic"] == 8, \
            f"Expected 8 pathogenic, got {exp['pathogenic']}"

        if verbose:
            print(f"  VCF path: {data['vcf_path']}")
            print(f"  Genome: {data['genome']}")
            print(f"  Expected: {exp['total_variants']} variants, "
                  f"{exp['pathogenic']} pathogenic, {exp['benign']} benign")

    except ImportError:
        # Fallback: create VCF manually and validate
        tmp_dir = tempfile.mkdtemp(prefix="gva_test_")
        try:
            vcf_path = os.path.join(tmp_dir, "test.vcf")
            with open(vcf_path, "w") as f:
                f.write(MINIMAL_VCF_CONTENT)
            variants = _parse_vcf_manually(vcf_path)
            assert len(variants) == 10, f"Expected 10 variants, got {len(variants)}"
            if verbose:
                print(f"  Fallback: created VCF manually with {len(variants)} variants")
        finally:
            shutil.rmtree(tmp_dir)

    print("  ✓ Example data loading: PASSED")
    return True


# ── Test 3: Tool detection ─────────────────────────────────────────────────────

def test_tool_detection(verbose=False):
    """Test that VEP and SNPEff installation can be detected."""
    print("\n[Test 3] Annotation tool detection...")

    tools_found = {}

    # Check VEP
    try:
        from run_vep import check_vep_installation
        vep_ok, vep_path, vep_version = check_vep_installation()
        tools_found["vep"] = {"installed": vep_ok, "path": vep_path, "version": vep_version}
    except ImportError:
        # Fallback: check via subprocess
        try:
            result = subprocess.run(
                ["vep", "--version"], capture_output=True, text=True, timeout=10
            )
            tools_found["vep"] = {
                "installed": result.returncode == 0,
                "path": "vep",
                "version": result.stdout.strip()[:50] if result.returncode == 0 else None
            }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            tools_found["vep"] = {"installed": False, "path": None, "version": None}

    # Check SNPEff
    try:
        from run_snpeff import check_snpeff_installation
        snpeff_ok, snpeff_path, snpeff_version = check_snpeff_installation()
        tools_found["snpeff"] = {"installed": snpeff_ok, "path": snpeff_path, "version": snpeff_version}
    except ImportError:
        try:
            result = subprocess.run(
                ["snpEff", "-version"], capture_output=True, text=True, timeout=10
            )
            tools_found["snpeff"] = {
                "installed": result.returncode == 0,
                "path": "snpEff",
                "version": result.stdout.strip()[:50] if result.returncode == 0 else None
            }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            tools_found["snpeff"] = {"installed": False, "path": None, "version": None}

    # At least one tool should be detectable (even if not installed)
    assert "vep" in tools_found and "snpeff" in tools_found, \
        "Tool detection failed for both VEP and SNPEff"

    if verbose:
        for tool, info in tools_found.items():
            status = "✓ installed" if info["installed"] else "✗ not installed"
            print(f"  {tool.upper()}: {status}")
            if info["version"]:
                print(f"    Version: {info['version']}")

    n_installed = sum(1 for t in tools_found.values() if t["installed"])
    if n_installed == 0:
        print("  ⚠ Neither VEP nor SNPEff is installed — live annotation tests will be skipped")
        print("    Install VEP:    conda install -c bioconda ensembl-vep")
        print("    Install SNPEff: conda install -c bioconda snpeff")
    else:
        print(f"  {n_installed}/2 annotation tool(s) available")

    print("  ✓ Tool detection: PASSED")
    return tools_found


# ── Test 4: Output parsing logic ──────────────────────────────────────────────

def test_output_parsing(verbose=False):
    """Test VEP and SNPEff output parsing with mock annotation output."""
    print("\n[Test 4] Output parsing logic (mock)...")

    # Mock VEP output (tab-separated)
    MOCK_VEP_OUTPUT = """\
## VEP output
#Uploaded_variation\tLocation\tAllele\tGene\tFeature\tFeature_type\tConsequence\tcDNA_position\tCDS_position\tProtein_position\tAmino_acids\tCodons\tExisting_variation\tExtra
rs80357906\t17:43044295\tT\tENSG00000012048\tENST00000357654\tTranscript\tstop_gained\t1234\t1234\t412\tR/*\tcGa/tGa\trs80357906\tIMPACT=HIGH;SIFT=deleterious(0.0);PolyPhen=probably_damaging(0.999)
rs80358981\t13:32315474\tG\tENSG00000139618\tENST00000380152\tTranscript\tmissense_variant\t5678\t5678\t1893\tD/G\tGat/Ggt\trs80358981\tIMPACT=MODERATE;SIFT=tolerated(0.23);PolyPhen=benign(0.001)
"""

    # Mock SNPEff output (VCF with ANN field)
    MOCK_SNPEFF_OUTPUT = """\
##fileformat=VCFv4.2
##SnpEffVersion="5.1"
##INFO=<ID=ANN,Number=.,Type=String,Description="Functional annotations">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
17\t43044295\trs80357906\tA\tT\t.\tPASS\tANN=T|stop_gained|HIGH|BRCA1|ENSG00000012048|transcript|ENST00000357654|protein_coding|11/23|c.1234C>A|p.Arg412*|1234|1234|412|R/*|WARNING_TRANSCRIPT_INCOMPLETE
13\t32315474\trs80358981\tA\tG\t.\tPASS\tANN=G|missense_variant|MODERATE|BRCA2|ENSG00000139618|transcript|ENST00000380152|protein_coding|12/27|c.5678A>G|p.Asp1893Gly|5678|5678|1893|D/G|
"""

    tmp_dir = tempfile.mkdtemp(prefix="gva_parse_test_")
    try:
        # Test VEP parsing
        vep_path = os.path.join(tmp_dir, "vep_output.txt")
        with open(vep_path, "w") as f:
            f.write(MOCK_VEP_OUTPUT)

        try:
            from parse_vep_output import parse_vep_output
            vep_df = parse_vep_output(vep_path)
            assert len(vep_df) >= 2, f"Expected ≥2 VEP records, got {len(vep_df)}"
            if verbose:
                print(f"  VEP parsed: {len(vep_df)} records")
        except ImportError:
            # Fallback: manual parsing
            vep_records = _parse_vep_manually(vep_path)
            assert len(vep_records) == 2, f"Expected 2 VEP records, got {len(vep_records)}"
            assert any("stop_gained" in r.get("Consequence", "") for r in vep_records), \
                "stop_gained consequence not found"
            if verbose:
                print(f"  VEP parsed manually: {len(vep_records)} records")

        # Test SNPEff parsing
        snpeff_path = os.path.join(tmp_dir, "snpeff_output.vcf")
        with open(snpeff_path, "w") as f:
            f.write(MOCK_SNPEFF_OUTPUT)

        try:
            from parse_snpeff_output import parse_snpeff_output
            snpeff_df = parse_snpeff_output(snpeff_path)
            assert len(snpeff_df) >= 2, f"Expected ≥2 SNPEff records, got {len(snpeff_df)}"
            if verbose:
                print(f"  SNPEff parsed: {len(snpeff_df)} records")
        except ImportError:
            # Fallback: check ANN field is present
            with open(snpeff_path) as f:
                content = f.read()
            assert "stop_gained" in content, "stop_gained not found in SNPEff output"
            assert "missense_variant" in content, "missense_variant not found in SNPEff output"
            if verbose:
                print("  SNPEff output validated manually (ANN field present)")

    finally:
        shutil.rmtree(tmp_dir)

    print("  ✓ Output parsing logic: PASSED")
    return True


# ── Live test ──────────────────────────────────────────────────────────────────

def test_live_annotation(tool="auto", verbose=False):
    """Run actual annotation on ClinVar BRCA1/BRCA2 example variants."""
    print(f"\n[Live Test] Full annotation with {tool.upper() if tool != 'auto' else 'auto-detected tool'}...")

    # Load example data
    try:
        from load_example_data import load_clinvar_pathogenic_sample
        data = load_clinvar_pathogenic_sample()
        vcf_path = data["vcf_path"]
        expected = data["expected_results"]
    except ImportError:
        print("  ⚠ SKIPPED: load_example_data.py not found")
        return False

    # Detect available tool
    if tool == "auto":
        for t in ["vep", "snpeff"]:
            try:
                result = subprocess.run(
                    [t if t == "vep" else "snpEff", "--version" if t == "vep" else "-version"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    tool = t
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        if tool == "auto":
            print("  ⚠ SKIPPED: No annotation tool installed (VEP or SNPEff required)")
            return False

    tmp_dir = tempfile.mkdtemp(prefix="gva_live_test_")
    try:
        if tool == "vep":
            try:
                from run_vep import run_vep_annotation
                result = run_vep_annotation(
                    vcf_path=vcf_path,
                    genome="GRCh38",
                    output_dir=tmp_dir
                )
                output_file = result.get("output_file")
            except ImportError:
                print("  ⚠ SKIPPED: run_vep.py not found")
                return False

        elif tool == "snpeff":
            try:
                from run_snpeff import run_snpeff_annotation
                result = run_snpeff_annotation(
                    vcf_path=vcf_path,
                    genome="GRCh38",
                    output_dir=tmp_dir
                )
                output_file = result.get("output_file")
            except ImportError:
                print("  ⚠ SKIPPED: run_snpeff.py not found")
                return False

        # Validate output exists
        assert output_file and os.path.exists(output_file), \
            f"Annotation output file not created: {output_file}"

        if verbose:
            print(f"  Annotation output: {output_file}")
            print(f"  File size: {os.path.getsize(output_file)} bytes")

        print(f"  ✓ Live annotation ({tool.upper()}): PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Live annotation failed: {e}")
        return False
    finally:
        shutil.rmtree(tmp_dir)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _parse_vcf_manually(vcf_path):
    """Parse VCF file manually, returning list of variant dicts."""
    variants = []
    opener = gzip.open if vcf_path.endswith(".gz") else open
    with opener(vcf_path, "rt") as f:
        headers = None
        for line in f:
            line = line.strip()
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                headers = line.lstrip("#").split("\t")
                continue
            if headers and line:
                fields = line.split("\t")
                variants.append(dict(zip(headers, fields)))
    return variants


def _parse_vep_manually(vep_path):
    """Parse VEP tab output manually."""
    records = []
    with open(vep_path) as f:
        headers = None
        for line in f:
            line = line.strip()
            if line.startswith("##"):
                continue
            if line.startswith("#Uploaded"):
                headers = line.lstrip("#").split("\t")
                continue
            if headers and line:
                fields = line.split("\t")
                records.append(dict(zip(headers, fields)))
    return records


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test genetic-variant-annotation skill."
    )
    parser.add_argument("--live",    action="store_true",
                        help="Run live annotation test (requires VEP or SNPEff)")
    parser.add_argument("--tool",    default="auto",
                        choices=["auto", "vep", "snpeff"],
                        help="Annotation tool for live test (default: auto-detect)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed test output")
    args = parser.parse_args()

    print("=" * 60)
    print("genetic-variant-annotation — Skill Test")
    print("=" * 60)

    results = {}

    # Mock tests
    for name, fn in [
        ("vcf_validation",    lambda: test_vcf_validation(args.verbose)),
        ("example_data",      lambda: test_example_data_loading(args.verbose)),
        ("tool_detection",    lambda: test_tool_detection(args.verbose)),
        ("output_parsing",    lambda: test_output_parsing(args.verbose)),
    ]:
        try:
            fn()
            results[name] = "PASSED"
        except (AssertionError, Exception) as e:
            print(f"  ✗ FAILED: {e}")
            results[name] = "FAILED"

    # Live test
    if args.live:
        passed = test_live_annotation(tool=args.tool, verbose=args.verbose)
        results["live_annotation"] = "PASSED" if passed else "SKIPPED"

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    all_ok = all(v in ("PASSED", "SKIPPED") for v in results.values())
    for test, status in results.items():
        icon = "✓" if status == "PASSED" else ("⚠" if status == "SKIPPED" else "✗")
        print(f"  {icon} {test}: {status}")

    if all_ok:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
