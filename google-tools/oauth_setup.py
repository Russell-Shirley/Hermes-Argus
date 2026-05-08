import sys
from google_tools.auth import run_oauth_flow


def main():
    print("Argus Google Workspace — OAuth Setup")
    print("-" * 40)
    print("A browser window will open. Log in with your Google account")
    print("and grant Argus access to Gmail, Calendar, and Tasks.")
    print("-" * 40)
    try:
        creds = run_oauth_flow()
        print()
        print("✅ Authorization complete!")
        print(f"   Token saved. Token expiry: {creds.expiry}")
        print("   You can now restart Argus to use Google Workspace tools.")
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Authorization failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
