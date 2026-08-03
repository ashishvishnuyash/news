#!/usr/bin/env python3
"""
The Republic Bulletin - Mouse Interactive Broadsheet TUI Application
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textual_app import BroadsheetApp
from api_client import BASE_URL

def main():
    parser = argparse.ArgumentParser(description="The Republic Bulletin - Mouse Interactive Broadsheet TUI")
    parser.add_argument("--url", type=str, default=BASE_URL, help="Backend API base URL (default: http://localhost:8000/api)")
    parser.add_argument("--role", type=str, choices=["superadmin", "admin", "editor", "journalist", "reader", "user"], help="Quick auto-login with demo role")
    args = parser.parse_args()

    app = BroadsheetApp(base_url=args.url)
    
    if args.role:
        target_user = "reader" if args.role in ("reader", "user") else args.role
        ok, msg = app.api.login(target_user, "password123")
        if ok and app.api.current_user:
            print(f"Quick authenticated as {app.api.current_user['role']}: {app.api.current_user['username']}")

    app.run()

if __name__ == "__main__":
    main()
