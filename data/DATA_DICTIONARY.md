# Data dictionary: `data/processed/pocket_money_clean.csv`

203 rows (one per respondent), 35 columns. Source: bilingual online survey, 22 Aug to 8 Sep 2023, collected by Vaishnavi Deshmukh and used with permission.
E-mail, timestamp and free-text suggestions were removed.

| Column | Type | Meaning / coding |
|--------|------|------------------|
| respondent_id | int | Row number after cleaning (not an original ID) |
| gender | category | Male / Female |
| age_group | category | 17, 18, 19, 20+ |
| stream | category | Science / Commerce / Arts |
| origin | category | Rural / Urban (home area) |
| living | category | With Parents / With Relatives / In room / In hostel |
| family_size_n | int | Family members; "More than 6" coded as 7 |
| earners | int | Number of earning members in the family |
| family_income_k | number | Monthly family income, band midpoint in Rs '000 (20, 40, 60, 85, 110) |
| income_label | category | Original band: 10-30k, 30-50k, 50-70k, 70-100k, >100k |
| income_group | category | Bands used for tests: 10-30k, 30-50k, 50-70k, 70k+ (top two merged) |
| recv_mode | category | How pocket money is received: Cash / Online / Both |
| pm_received_raw | text | Answer exactly as given (ranges and free text kept) |
| pm_received_rs | number | Monthly pocket money in Rs; ranges converted to midpoint; free text such as "only when needed" and blanks = missing (10) |
| log_pm | number | Natural log of pm_received_rs |
| pm_outlier_iqr | 0/1 | 1 if pm_received_rs is above Q3 + 1.5 x IQR (Rs 3,450). Flagged, not removed |
| spent_pct | number | % of pocket money spent, band midpoint (typed "1" treated as 100) |
| saved_pct | number | % of pocket money saved, band midpoint (typed "0" = 0) |
| spent_plus_saved | number | spent_pct + saved_pct, a consistency check (about 100 expected) |
| use_academic, use_personal, use_lending, use_other | 0/1 | What pocket money is used for (multiple answers allowed) |
| app_phonepe, app_gpay, app_paytm, app_other | 0/1 | Payment apps used (multiple answers allowed) |
| app_none_reported | 0/1 | 1 if the app question was left blank |
| invests | category | Yes / No: invests savings |
| invest_where | category | Stock Market / FD / Other (only for investors) |
| invests_flag | 0/1 | invests == Yes |
| same_every_month | category | Yes / No: needs the same amount every month |
| same_every_month_flag | 0/1 | same_every_month == Yes |
| male | 0/1 | gender == Male |
| urban | 0/1 | origin == Urban |

Not published: department (free text) and the parents' occupations were removed because, in a small campus sample, they could identify individual respondents. No analysis uses them.
