# Raw data (not included)

The original Google-Form export (`Pocket_Money_Dataset.xlsx`) contains respondents' e-mail addresses and
free-text answers, so it is **not committed** (see `.gitignore`).

To re-run the whole pipeline from scratch, place the file here as `data/raw/Pocket_Money_Dataset.xlsx`
(sheet 1 = survey responses) and run `python src/01_clean_data.py`.
The anonymised, cleaned result is already provided in `data/processed/pocket_money_clean.csv`,
so steps 2 and 3 can be run without the raw file.
