# Hourly Rate Flow

A customizable desktop application for tracking hourly work and earnings with configurable rates. Perfect for freelancers, servers, bartenders, contractors, and any hourly worker.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## Features

- **Customizable Rates**: Set your own hourly wage and optionally include average tips
- **Work Period Tracking**: Organize your hours by customizable periods (weekly, bi-weekly, monthly, etc.)
- **Visual Earnings Display**: See your projected earnings with a visual chart
- **Note System**: Add notes to your work entries for context
- **Data Persistence**: All data is saved locally using SQLite
- **Export Capability**: Export your data to a text file for record-keeping
- **Zero Setup Required**: Just run the script and start tracking

## Installation

### Prerequisites
- Python 3.8 or higher
- Tkinter (usually included with Python)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Luvvydev/hourly-rate-flow.git
   cd hourly-rate-flow

## Usage

### First Launch
When you first run the app, it will use default rates:
- Base rate: $7.00/hour
- Average tips: $23.15/hour (optional)

### Configuring Your Rates
1. Click the **"⚙ Settings"** button in the top-right corner
2. Set your **Base Hourly Rate** (your wage before tips)
3. Choose whether to **Include tips** in calculations
4. If including tips, set your **Average tips per hour**
5. Click **"Save & Apply"**

### Logging Hours
1. **Date**: Defaults to today (can be changed)
2. **Hours**: Enter hours worked (use quick buttons 1h-8h for convenience)
3. **Note** (optional): Click "➕ Add Note" to add context
4. Click **"Add Entry"** or press **Enter**

### Features Overview
- **Quick Hour Buttons**: 1h-8h presets for fast entry
- **Period Management**: Start new periods to organize your work
- **Visual Progress**: See your earnings projection visually
- **Recent Entries**: View, scroll, and manage your logged hours
- **Data Export**: Export all data to a text file
- **Clear All Data**: Reset the application completely

## Data Storage

Your data is stored in two locations:

1. **Database**: `~/.ledgerflow.db` (SQLite database)
   - Stores all your work entries and periods
   - Automatically created in your home directory

2. **Settings**: `~/.ledgerflow_settings.json`
   - Stores your configured rates and current period
   - Persists between sessions
