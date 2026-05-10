"""Verify deployment scripts produce correct output"""
import os
import yaml
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROVISION_SCRIPT = PROJECT_ROOT / "deploy" / "provision.sh"
TEMPLATES_DIR = PROJECT_ROOT / "deploy" / "templates"


def test_provision_script_exists():
    assert PROVISION_SCRIPT.exists()
    # Executable bit check is Unix-specific; skip on Windows
    import os as _os
    if _os.name != "nt":
        assert PROVISION_SCRIPT.stat().st_mode & 0o100


def test_provision_script_shebang():
    content = PROVISION_SCRIPT.read_text()
    assert content.startswith("#!/bin/bash")
    assert "set -euo pipefail" in content


def test_provision_script_has_preset_flag():
    content = PROVISION_SCRIPT.read_text()
    assert "--preset" in content


def test_provision_script_has_modules_flag():
    content = PROVISION_SCRIPT.read_text()
    assert "--modules" in content


def test_provision_script_has_cloud_flag():
    content = PROVISION_SCRIPT.read_text()
    assert "--cloud" in content


def test_all_preset_files_exist():
    for name in ["construction", "dental", "retail"]:
        assert (TEMPLATES_DIR / f"{name}.yaml").exists()


def test_construction_preset_valid_yaml():
    with open(TEMPLATES_DIR / "construction.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["org_type"] == "construction"
    assert "ar_collections" in preset["modules"]
    assert "voucher_processing" in preset["modules"]


def test_dental_preset_valid_yaml():
    with open(TEMPLATES_DIR / "dental.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["org_type"] == "dental_practice"
    assert preset["review_rules"]["hippa_compliant"] is True


def test_retail_preset_valid_yaml():
    with open(TEMPLATES_DIR / "retail.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["org_type"] == "retail"
    assert "inventory" in preset["modules"]


def test_all_presets_inherit_icm_base():
    for preset_name in ["construction", "dental", "retail"]:
        with open(TEMPLATES_DIR / f"{preset_name}.yaml") as f:
            preset = yaml.safe_load(f)
        assert "icm_base" in preset["modules"], f"{preset_name} missing icm_base"


def test_all_presets_have_review_rules():
    for preset_name in ["construction", "dental", "retail"]:
        with open(TEMPLATES_DIR / f"{preset_name}.yaml") as f:
            preset = yaml.safe_load(f)
        rules = preset.get("review_rules", {})
        assert "collection_letter_auto_approve" in rules, \
            f"{preset_name} missing review rule"
        assert rules["collection_letter_auto_approve"] is False, \
            f"{preset_name}: collection_letter_auto_approve must be False"


def test_apply_preset_script_exists():
    assert (PROJECT_ROOT / "deploy" / "apply_preset.py").exists()


def test_apply_preset_script_shebang():
    path = PROJECT_ROOT / "deploy" / "apply_preset.py"
    content = path.read_text()
    assert content.startswith("#!/usr/bin/env python3")


def test_onboarding_checklist_exists():
    assert (PROJECT_ROOT / "deploy" / "ONBOARDING.md").exists()


def test_onboarding_checklist_has_sections():
    content = (PROJECT_ROOT / "deploy" / "ONBOARDING.md").read_text()
    assert "## Pre-Deployment" in content
    assert "## Provisioning" in content
    assert "## Validation" in content
    assert "## Client Onboarding" in content
    assert "## Day 1 Monitoring" in content


def test_all_presets_have_payment_terms():
    for preset_name in ["construction", "dental", "retail"]:
        with open(TEMPLATES_DIR / f"{preset_name}.yaml") as f:
            preset = yaml.safe_load(f)
        assert "payment_terms" in preset, f"{preset_name} missing payment_terms"
        assert preset["payment_terms"] in ["net30", "net60"]


def test_construction_preset_has_high_threshold():
    with open(TEMPLATES_DIR / "construction.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["review_rules"]["voucher_auto_post_threshold"] >= 0.85


def test_retail_preset_has_low_stock_alert():
    with open(TEMPLATES_DIR / "retail.yaml") as f:
        preset = yaml.safe_load(f)
    assert preset["review_rules"]["low_stock_alert_auto"] is True
