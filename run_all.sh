#!/usr/bin/env bash
# Reproduce everything: clean data -> analysis -> PDF report
set -e
python src/01_clean_data.py     # needs data/raw/Pocket_Money_Dataset.xlsx (skip if you only have the processed CSV)
python src/02_analysis.py
python src/03_build_report.py
