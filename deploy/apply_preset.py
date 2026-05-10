#!/usr/bin/env python3
"""Apply org-type preset overrides to a provisioned Hermes-Argus instance."""
import sys
import os
from pathlib import Path

try:
    import yaml
except ImportError:
    print(" PyYAML not found. Install: pip install pyyaml")
    sys.exit(1)


def apply_preset(preset_file: str, org_dir: str):
    with open(preset_file) as f:
        preset = yaml.safe_load(f)

    org_type = preset.get("org_type", "unknown")
    review_rules = preset.get("review_rules", {})

    # Update Hermes config with org-specific settings
    config_path = Path(org_dir) / "config" / "hermes.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}

        # Apply review rules
        if "approvals" not in config:
            config["approvals"] = {}
        config["approvals"]["mode"] = "manual"

        # Apply voucher threshold
        if "voucher_auto_post_threshold" in review_rules:
            threshold = review_rules["voucher_auto_post_threshold"]
            env_path = Path(org_dir) / ".env"
            with open(env_path, "a") as env_f:
                env_f.write(f"\nVOUCHER_CONFIDENCE_THRESHOLD={threshold}")

        # Apply HIPAA flag
        if review_rules.get("hippa_compliant"):
            config["security"] = config.get("security", {})
            config["security"]["data_retention_days"] = 2555
            config["security"]["encrypt_at_rest"] = True

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    print(f" Applied {org_type} preset overrides to {org_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: apply_preset.py <preset_file> <org_dir>")
        sys.exit(1)
    apply_preset(sys.argv[1], sys.argv[2])
