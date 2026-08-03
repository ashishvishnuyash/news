# 🗞️ The Republic Bulletin - Mouse Interactive Broadsheet TUI

A full-featured, **100% Mouse-Interactive** 1800s broadsheet newspaper Terminal User Interface (TUI) built with **Textual** and connected to the FastAPI backend API (`http://localhost:8000/api`).

---

## 🖱️ Mouse-Interactive Features

- **Full Mouse Navigation**: Click tabs, buttons, section filters, data table rows, inputs, text areas, toggles, and modals with your mouse!
- **Mouse Wheel Scrolling**: Scroll through front page articles, review queues, and markdown article broadside proofs.
- **Interactive Modals**: Click any article row to open a full **Article Reading Modal** overlay with scrollable content, print button, and a live reader response submission form!
- **Clickable Role Desk Switching**: One-click staff role buttons (`👑 Super Admin`, `🛡️ Chief Admin`, `✍️ Editor`, `✒️ Journalist`, `👤 Reader`).

---

## 🚀 Quick Start

### 1. Installation
```bash
cd TUI
pip install -r requirements.txt
```

### 2. Launching the Mouse TUI Application

Run default mouse-interactive TUI:
```bash
python main.py
# or
python textual_app.py
```

### 3. Quick Role Direct Launch Flags
```bash
python main.py --role superadmin    # Central Publication Control Desk
python main.py --role admin         # Operations & User Registry Desk
python main.py --role editor        # Editorial Review Board Queue
python main.py --role journalist    # Press Correspondent Workspace
python main.py --role reader        # Subscriber Front Page Desk
```

---

## 🏛️ Supported Desks & Roles

| Desk Tab | Role Scope | Mouse Controls & Key Features |
| :--- | :--- | :--- |
| **📰 Front Page Broadsheet** | All Readers / Staff | Clickable section filter buttons (`ALL`, `POLITICS`, `WORLD`, `ECONOMY`, `TECH`, `OPINION`), live search bar, interactive article `DataTable`. Clicking any row opens full article reading modal with comments. |
| **✒️ Press Correspondent Desk** | Journalist / Editors | Authored dispatches `DataTable`, clickable compose form (`Title`, `Summary`, `Category`, `Content TextArea`), `[Save Draft]` & `[Submit to Review Board]` buttons. |
| **✍️ Editorial Review Board** | Editor / Admin | Filter queue buttons (`SUBMITTED`, `DRAFT`, `PUBLISHED`, `REJECTED`), click rows to proof content, `[✓ APPROVE & PUBLISH]`, `[X REJECT WITH NOTES]`. |
| **🛡️ Operations Desk** | Chief Admin / SuperAdmin | Live metrics summary cards, User Registry `DataTable`, Articles Moderation `DataTable` with clickable `[Delete Dispatch]` button. |
| **👑 Super Admin Desk** | Super Admin | Publication Title & Motto inputs, Breaking News Ticker switch & alert text input, Category Taxonomy management, Feature Flags switches. |
| **👤 Member Dossier** | Authenticated Users | Profile details card, email & bio inputs, passphrase change form with clickable `[Save Dossier]` button. |
| **🔐 Sign In / Roles** | All Users | Clickable one-click demo role selector buttons for instant authentication. |
