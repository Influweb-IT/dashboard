import numpy as np
import geopandas as gpd
import pgeocode
import pandas as pd
from collections import defaultdict
import os
import sys
import re
import datetime
from datetime import date, timedelta

from season_window import YEAR_MIN, YEAR_MAX, current_season, last_week_in_season

# override with env variables for local development
_HERE = os.path.dirname(os.path.abspath(__file__))
RAW_ROOT = os.environ.get('RAW_DIR', '/data/raw')
output_dir = os.environ.get('DASHBOARD_DATA_DIR', '/data/dashboard')


def _find_latest_raw_dir(root: str) -> str:
    """Return path of the most recent <root>/<YYYY-Www>/ that has a .READY sentinel.
    Override with the RAW_WEEK env var (e.g. RAW_WEEK=2026-W19)."""
    week_override = os.environ.get('RAW_WEEK')
    if week_override:
        d = os.path.join(root, week_override)
        if not os.path.isdir(d):
            raise FileNotFoundError(f"RAW_WEEK={week_override} not found under {root}")
        return d
    pat = re.compile(r'^\d{4}-W\d{2}$')
    candidates = [
        os.path.join(root, name)
        for name in sorted(os.listdir(root))
        if pat.match(name)
        and os.path.isdir(os.path.join(root, name))
        and os.path.exists(os.path.join(root, name, '.READY'))
    ]
    if not candidates:
        sys.exit(f'### no ready raw export found under {root} ###\n')
    return candidates[-1]


# Convert weeks with formats like 2014-2 to proper format 2014-02
def fix_yearweek(date_string):
    year, week = map(lambda x: int(x), date_string.split('-'))
    fixed = "{0}-{1:02d}".format(year, week)

    assert re.match(r"\d{4}-\d{2}$", fixed)
    return fixed


def weekMinus(week, minusweek):
    # week is a string 'yyyy-w'
    yr, wk = map(lambda x: int(x), week.split('-'))
    mid_date = getMiddleDayOfWeek(yr, wk)
    res_date = mid_date - timedelta(days=7 * minusweek)
    isoyear, isoweek, isoday = res_date.isocalendar()
    return str(isoyear) + '-' + str(isoweek)


def getMiddleDayOfWeek(year, week):
    d = datetime.date(year, 1, 1)
    if d.weekday() > 3:
        d = d + timedelta(7 - d.weekday())
    else:
        d = d - timedelta(d.weekday())
    dlt = timedelta(days=(week - 1) * 7)
    return d + dlt + timedelta(days=3)


def weekPlusOne(week):
    # week is a string 'yyyy-w'
    yr, wk = map(lambda x: int(x), week.split('-'))
    mid_date = getMiddleDayOfWeek(yr, wk)
    res_date = mid_date + timedelta(days=7)
    isoyear, isoweek, isoday = res_date.isocalendar()
    return str(isoyear) + '-' + str(isoweek)


def days_difference(date1, date2):
    y1, m1, d1 = map(lambda x: int(x), date1.split('-'))
    y2, m2, d2 = map(lambda x: int(x), date2.split('-'))
    delta_days = (datetime.date(y1, m1, d1) - datetime.date(y2, m2, d2)).days
    return delta_days


def get_onset_date(submission_date, symptoms_date, fever_date):
    onset_date = submission_date
    if pd.notnull(symptoms_date):
        if 0 <= days_difference(submission_date, symptoms_date) <= 15:
            onset_date = symptoms_date
    elif pd.notnull(submission_date) and pd.notnull(fever_date):
        if 0 <= days_difference(submission_date, fever_date) <= 15:
            onset_date = fever_date
    return onset_date


def get_week_of_activity(global_id, submission_weeks):
    activity_weeks = []
    for week in submission_weeks:
        wk_start, wk_end = fix_yearweek(weekMinus(week, 2)), fix_yearweek(weekMinus(week, -2))
        wk = wk_start
        while wk <= wk_end:
            activity_weeks.append(wk)
            wk = fix_yearweek(weekPlusOne(wk))
    return sorted(set(activity_weeks))


def yearweek_to_ts(x):
    year = x.split('-')[0]
    week = x.split('-')[1]
    date = "{}-{}-1".format(year, week)
    dt = datetime.datetime.strptime(date, "%Y-%W-%w")
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'


def get_ILI_ECDC(row):
    ILI = False
    if row.symptoms == True:  # noqa: E712
        if row['Sudden onset'] == True or row['Sudden fever'] == True:  # noqa: E712
            if (row.Fever == True or row.Chills == True or row['Malaise'] == True  # noqa: E712
                    or row.Headache == True or row['Muscle/joint pain'] == True):  # noqa: E712
                if (row['Sore throat'] == True or row.Cough == True  # noqa: E712
                        or row['Shortness of breath'] == True):  # noqa: E712
                    ILI = True
    return ILI


def get_ARI(row):
    ARI = False
    if row.symptoms == True:  # noqa: E712
        if row['Sudden onset'] == 0.0:  # 0 = sudden onset
            if (row.Cough == True or row['Sore throat'] == True  # noqa: E712
                    or row['Shortness of breath'] == True  # noqa: E712
                    or row['Runny or blocked nose'] == True):  # noqa: E712
                ARI = True
    return ARI

# Return previous week: lastweek(date.today()) -> '2019-46'


def lastweek(today=date.today()):
    prev = today - timedelta(days=7)
    return fix_yearweek(str(prev.isocalendar()[0]) + '-' + str(prev.isocalendar()[1]))


def unite(x):
    aa = np.where(x)[0]
    if len(aa) > 0:
        return int(aa[0])
        print(aa)
    else:
        return np.nan


def translate(entry):
    if entry == 'f':
        entry = False
    elif entry == 'FALSE':
        entry = False
    elif entry == 't':
        entry = True
    elif entry == 'TRUE':
        entry = True
    return entry


def get_age(x):
    subm = int(x.intake_submission[:4])
    if any([x.version == '22-12-2', x.version == '21-11-1', x.version == '23-10-1']):
        new_year = int(datetime.datetime.fromtimestamp(int(x.Q2)).strftime('%Y'))
        if subm - new_year < 0:
            print(x.Q2)
        return subm - new_year

    else:
        if '/' in x.Q2 or '-' in x.Q2:
            year = int(x.Q2[:4])
            if subm - year < 0:
                print(x.Q2)
            return subm - year


def get_age_class(x):
    if x < 18 and x > 0:
        return '<18'
    elif x >= 18 and x <= 40:
        return '18-40'
    elif x > 40 and x <= 65:
        return '41-65'
    elif x > 65:
        return '>65'
    else:
        return 'nan'


def occupation(x):
    if str(x) != 'nan':
        x = int(x)
        if x == 0:
            return 'full_time'
        elif x == 1:
            return 'part_time'
        elif x == 2:
            return 'self-employed'
        elif x == 3:
            return 'student'
        elif x == 4:
            return 'homemaker'
        elif x == 5:
            return 'unemployed'
        elif x == 6:
            return 'on leave'
        elif x == 7:
            return 'retired'
        elif x == 8:
            return 'other'


def schooling(x):
    if x == 0:
        return 'none'
    elif x == 1:
        return 'int_school'
    elif x == 2:
        return 'high_school'
    elif x == 3:
        return 'bachelor'
    elif x == 4:
        return 'master_phd'
    elif x == 5:
        return 'student'


def get_edu(x):
    if str(x) == 'None' or str(x) == 'none' or x == np.nan or x == 'student':
        return 'elementary'
    elif x == 'int_school' or x == 'high_school':
        return 'secondary'
    elif x == 'master_phd' or x == 'bachelor':
        return 'higher'


def change_regname(x):
    if x == 'Emilia-Romagna':
        return 'Emilia-Romagna'
    elif x == "Valle d'Aosta/Vallée d'Aoste":
        return "Valle d'Aosta"
    elif x == "Valle d'Aosta / Vallée d'Aoste":
        return "Valle d'Aosta"
    elif x == 'Trentino-Alto Adige/Südtirol':
        return 'Trentino-Alto Adige'
    elif x == 'Trentino-Alto Adige / Südtirol':
        return 'Trentino-Alto Adige'
    elif x == 'Trentino Alto Adige / Südtirol':
        return 'Trentino-Alto Adige'
    elif x == 'Abruzzi':
        return 'Abruzzo'
    elif x == "Valle D'Aosta":
        return "Valle d'Aosta"
    else:
        return x


dates = datetime.date.today()

last_week = lastweek(dates)

my_yearweek = last_week
min_year = str(YEAR_MIN)
max_year = str(YEAR_MAX)
previous_season = str(int(max_year) - 2) + '-' + str(int(max_year) - 1)
first_day = min_year + '-11-01'  # from Nov 1stM
last_day = max_year + '-05-01'  # to May 1st
print(f"Min year: {min_year}, Max year: {max_year}, Prev season: {previous_season}")
print(f"First day: {first_day}, Last day: {last_day}")

# CALENDAR
delta = timedelta(days=1)
curr, end = datetime.date(YEAR_MIN, 11, 1), datetime.date.today()  # datetime.date(YEAR_MAX, 5, 1)
date_week = dict()
llyearweek, week_to_consider = [], []
while curr <= end:
    yearweek = fix_yearweek(str(curr.isocalendar()[0]) + '-' + str(curr.isocalendar()[1]))
    date = curr.isoformat()
    date_week[date] = yearweek
    if date >= first_day and date <= last_day:
        if yearweek <= my_yearweek and yearweek not in week_to_consider:
            week_to_consider.append(yearweek)
        if yearweek not in llyearweek:
            llyearweek.append(yearweek)
    curr += delta

date_season = dict()
season_week = defaultdict(set)
week_season = {}

for yr_min in range(YEAR_MIN, YEAR_MAX, 1):
    yr_max = yr_min + 1
    for date in date_week.keys():
        from_ = datetime.date(yr_min, 11, 1).isoformat()
        to_ = datetime.date(yr_max, 5, 1).isoformat()
        if str(yr_min) + '-11-01' <= date <= str(yr_max) + '-05-01':
            season = str(yr_min) + '-' + str(yr_max)
            date_season[date] = season
            date_f = datetime.datetime.strptime(str(date), '%Y-%m-%d')
            weeknr = str(date_f.isocalendar().year) + '-' + str(date_f.isocalendar().week).zfill(2)
            season_week[season].add(weeknr)
            week_season[weeknr] = season

seasons = set(season_week.keys())

date_season = dict()
for yr_min in range(YEAR_MIN, YEAR_MAX, 1):
    yr_max = yr_min + 1
    for date in date_week.keys():
        from_ = datetime.date(yr_min, 11, 1).isoformat()
        to_ = datetime.date(yr_max, 5, 1).isoformat()
        if str(yr_min) + '-11-01' <= date <= str(yr_max) + '-05-01':
            season = str(yr_min) + '-' + str(yr_max)
            date_season[date] = season


raw_dir = _find_latest_raw_dir(RAW_ROOT)
print(f"Reading raw export from {raw_dir}", flush=True)

# Only the intake columns the analysis needs
INTAKE_USECOLS = [
    'participantID', 'version', 'submitted',
    'intake.Q1',      # gender
    'intake.Q2',      # age / year of birth
    'intake.Q3.0',    # postal code
    'intake.Q4',      # occupation
    'intake.Q4d.0', 'intake.Q4d.1', 'intake.Q4d.2',
    'intake.Q4d.3', 'intake.Q4d.4', 'intake.Q4d.5',  # education
]

intake_complete = pd.read_csv(
    os.path.join(raw_dir, 'intake.csv'),
    usecols=INTAKE_USECOLS,
    low_memory=False,
)

# INTAKE

intake_complete['timestamp'] = intake_complete.submitted.apply(
    lambda d: pd.to_datetime(int(d), unit='s'))
intake_complete.timestamp = pd.to_datetime(
    intake_complete.timestamp, utc=True).apply(
        lambda d: d.strftime('%Y-%m-%d %H:%M:%S'))
intake_complete = intake_complete.sort_values("timestamp", ascending=True)

# remove surveys with no global_id , if any
intake_complete = intake_complete[pd.notnull(intake_complete.participantID)]

# rename cols
intake_complete.rename(columns={'timestamp': 'intake_timestamp'}, inplace=True)
intake_complete.drop_duplicates('intake_timestamp', keep='last', inplace=True)

# add date, province and vaccine
intake_complete.insert(4, "intake_submission", intake_complete.intake_timestamp.str.split().str[0])

# gender
intake_complete['gender'] = intake_complete['intake.Q1'].map(
    {0: 'Male', 1: 'Female'}).fillna('Other')

# age
intake_complete[['Q2']] = intake_complete[['intake.Q2']].astype(str)
intake_complete['age'] = intake_complete.apply(lambda x: get_age(x), axis=1)
intake_complete['age_class'] = intake_complete[['age']].map(lambda x: get_age_class(x))

# province
intake_complete['intake.Q3.0'] = intake_complete['intake.Q3.0'].apply(
    lambda x: str(x).replace('.', '')).astype('str')
intake_complete['CAP'] = intake_complete['intake.Q3.0'].apply(
    lambda x: str(x)[:-1].zfill(5) if pd.notna(x) else np.nan)

nomi = pgeocode.Nominatim('it')


def assign_reg(x):
    try:
        y = nomi.query_postal_code(x).state_name
    except BaseException:
        y = np.nan
    return y


intake_complete['reg'] = intake_complete.CAP.apply(
    lambda x: assign_reg(x) if x.isdigit() else np.nan)
intake_complete['reg'] = intake_complete['reg'].apply(lambda x: change_regname(x))

# add occupation and education degree
intake_complete[['Q4',
                 'Q4d_0',
                 'Q4d_1',
                 'Q4d_2',
                 'Q4d_3',
                 'Q4d_4',
                 'Q4d_5']] = intake_complete[['intake.Q4',
                                              'intake.Q4d.0',
                                              'intake.Q4d.1',
                                              'intake.Q4d.2',
                                              'intake.Q4d.3',
                                              'intake.Q4d.4',
                                              'intake.Q4d.5']].map(lambda x: translate(x))
intake_complete['occupation'] = intake_complete['intake.Q4'].apply(lambda x: occupation(x))
_edu_cols = ['Q4d_0', 'Q4d_1', 'Q4d_2', 'Q4d_3', 'Q4d_4', 'Q4d_5']
intake_complete['education'] = intake_complete[_edu_cols].apply(lambda x: unite(x), axis=1)
intake_complete['edu'] = intake_complete['education'].apply(lambda x: schooling(x))
intake_complete['education'] = intake_complete['edu'].apply(lambda x: get_edu(x))

intake_complete = intake_complete[intake_complete.age_class != 'nan']

intake = intake_complete[["participantID", "age_class", "gender", "reg",
                          "edu", "occupation", "intake_timestamp", "intake_submission"]]

# Only the weekly columns the analysis uses
WEEKLY_USECOLS = [
    'participantID', 'submitted',
    'weekly.HS.Q3.0',
    'weekly.HS.Q4.0',
    'weekly.HS.Q5',
    'weekly.HS.Q6.1',
    'weekly.HS.Q6b',
] + [f'weekly.Q1.{i}' for i in range(24)]

# Q1.* are boolean-like strings ('TRUE'/'FALSE'/'t'/'f') so we can use category to cut memory.
# HS.Q5 and HS.Q6b are integer codes compared with == 0
# we need to keep them as numeric so the comparison works correctly
# (category would store them as string '0', '1')
WEEKLY_DTYPES = {col: 'category' for col in [f'weekly.Q1.{i}' for i in range(24)]}

weekly_complete = pd.read_csv(
    os.path.join(raw_dir, 'weekly.csv'),
    usecols=WEEKLY_USECOLS,
    dtype=WEEKLY_DTYPES,
    low_memory=False,
)


# WEEKLY

def transf_date(x):
    if pd.notnull(x):
        newx = pd.to_datetime(int(x), unit='s')
        return newx
    else:
        return ''


weekly_complete['weekly.HS.Q3.0'] = weekly_complete['weekly.HS.Q3.0'].apply(
    lambda d: transf_date(d))
weekly_complete['weekly.HS.Q4.0'] = weekly_complete['weekly.HS.Q4.0'].apply(
    lambda d: transf_date(d))
weekly_complete['weekly.HS.Q6.1'] = weekly_complete['weekly.HS.Q6.1'].apply(
    lambda d: transf_date(d))

weekly_complete['timestamp'] = weekly_complete.submitted.apply(
    lambda d: pd.to_datetime(int(d), unit='s', errors='coerce'))
weekly_complete.timestamp = pd.to_datetime(
    weekly_complete.timestamp, utc=True).apply(
        lambda d: d.strftime('%Y-%m-%d %H:%M:%S'))
weekly_complete = weekly_complete.sort_values("timestamp", ascending=True)
weekly_complete = weekly_complete[weekly_complete.timestamp <= dates.strftime('%Y-%m-%d %H:%M:%S')]


weekly_complete['weekly.HS.Q3.0'] = pd.to_datetime(
    weekly_complete['weekly.HS.Q3.0'],
    utc=True,
    errors='coerce').dt.strftime('%Y-%m-%d')
weekly_complete['weekly.HS.Q4.0'] = pd.to_datetime(
    weekly_complete['weekly.HS.Q4.0'],
    utc=True,
    errors='coerce').dt.strftime('%Y-%m-%d')
weekly_complete['weekly.HS.Q6.1'] = pd.to_datetime(
    weekly_complete['weekly.HS.Q6.1'],
    utc=True,
    errors='coerce').dt.strftime('%Y-%m-%d')

weekly_complete['Sudden onset'] = weekly_complete['weekly.HS.Q5'].apply(
    lambda x: True if x == 0 else False)
weekly_complete['Sudden fever'] = weekly_complete['weekly.HS.Q6b'].apply(
    lambda x: True if x == 0 else False)

# homogenize true and false
_symptom_src = [f'weekly.Q1.{i}' for i in range(24)]
_symptom_dst = [
    'Q1_0', 'Fever', 'Chills', 'Runny or blocked nose', 'Sneezing',
    'Sore throat', 'Cough', 'Shortness of breath', 'Headache',
    'Muscle/joint pain', 'Chest pain', 'Malaise', 'Loss of appetite',
    'Coloured sputum', 'Watery, bloodshot eyes', 'Nausea', 'Vomiting',
    'Diarrhoea', 'Stomach ache', 'Other', 'Rash', 'Loss of taste',
    'Nose bleed', 'Loss of smell',
]
weekly_complete[_symptom_dst] = weekly_complete[_symptom_src].map(lambda x: translate(x))

# remove surveys with no global_id, if any, and consider only surveys
# which have a corresponding intake survey
weekly_complete = weekly_complete[pd.notnull(weekly_complete.participantID)]
weekly_complete = weekly_complete[weekly_complete.participantID.isin(
    intake.participantID.unique())]

# add cols
weekly_complete.rename(columns={'timestamp': 'weekly_timestamp'}, inplace=True)
weekly_complete.insert(3, "submission_date", weekly_complete.weekly_timestamp.str.split().str[0])
weekly_complete.insert(4, "submission_week", weekly_complete.submission_date.map(date_week))
weekly_complete.insert(5, "season", weekly_complete.submission_date.map(date_season))

# keep only current season
weekly_complete = weekly_complete[weekly_complete.season == current_season]

# remove duplicates within the same week, keeping the last one
weekly = weekly_complete.drop_duplicates(
    ['participantID', 'submission_week'], keep='last', inplace=False)


# WEEKLY + INTAKE
# Merge weekly and intake according to the most recent intake per each weekly_survey submitted
weekly_sorted = weekly.assign(_ts=pd.to_datetime(weekly.weekly_timestamp)).sort_values("_ts")
intake_sorted = intake.assign(_ts=pd.to_datetime(intake.intake_timestamp)).sort_values("_ts")
data = pd.merge_asof(
    weekly_sorted, intake_sorted,
    on="_ts", by="participantID", direction="backward",
).drop(columns=["_ts"])
assert data.shape[0] == weekly.shape[0]


all_weeks = sorted(set(data.submission_week.dropna().values))  # all weeks in the period
real_weeks = sorted(set(week_season.keys()))  # only weeks in seasons

data = data[~pd.isna(data.season)]


# ACTIVE USERS (in real-time):
# - AT LEAST 2 symptoms surveys
# - WINDOW OF PARTICIPATION: +/- 2 WEEKS AROUND THE WEEK OF REPORTING

# keep only surveys of participants who submitted >= 2 symptoms surveys
data = data.groupby('participantID').filter(lambda x: len(x) > 1)
if data.empty:
    sys.exit('### no active users ###\n')


# get num. of active users per week
weekly_active_user = {}
for participantID, group in data.groupby('participantID'):
    activity_weeks = get_week_of_activity(participantID, group.submission_week)
    for wk in activity_weeks:
        weekly_active_user.setdefault(wk, 0)
        weekly_active_user[wk] += 1

wau = pd.Series(weekly_active_user).reindex(real_weeks).sort_index()

all_dates = sorted(pd.Series(date_week.keys()))
all_symptoms = [
    'Fever', 'Chills', 'Runny or blocked nose', 'Sneezing',
    'Sore throat', 'Cough', 'Shortness of breath', 'Headache',
    'Muscle/joint pain', 'Chest pain', 'Malaise', 'Loss of appetite',
    'Coloured sputum', 'Watery, bloodshot eyes', 'Nausea', 'Vomiting',
    'Diarrhoea', 'Stomach ache', 'Other', 'Rash', 'Loss of taste',
    'Nose bleed', 'Loss of smell', 'Sudden onset', 'Sudden fever',
]

all_weeks_tf = [yearweek_to_ts(x) for x in all_weeks]
real_weeks_tf = [yearweek_to_ts(x) for x in real_weeks]


data_ILI = data.copy(deep=True)
data_ILI = data_ILI[data_ILI.season.isin(seasons)]  # get only weeks in seasons

ILI_weeks = set(data_ILI.submission_week)
submission_weeks = [x for x in list(week_season.keys()) if x <= last_week_in_season]  # ILI_weeks

data_ILI['symptoms'] = data_ILI['weekly.Q1.0'].apply(lambda x: False if x == True else True)  # noqa: E712, E501

# Merge episodes

# define first_survey ever for each user
data_ILI['first_survey'] = data_ILI.groupby(['participantID'])['submission_week'].transform('min')

data_ILI['ILI'] = data_ILI.apply(lambda row: get_ILI_ECDC(row), axis=1)
data_ILI['ARI'] = data_ILI.apply(lambda row: get_ARI(row), axis=1)

# define onset week based on reported onset or reported fever onset for ILI and ARI only
data_ILI['onset_week'] = data_ILI.apply(
    lambda row: get_onset_date(
        row.submission_date,
        row['weekly.HS.Q3.0'],
        row['weekly.HS.Q6.1']) if any(
            [
                row['ILI'] == True,  # noqa: E712
                row['ARI'] == True]) else np.nan,  # noqa: E712
    axis=1).map(date_week)  # only if ILI or ARI

# Remove first submissions

# correction for first submitted ILI survey ever
data_ILI.loc[(data_ILI['ILI'] == True) & (data_ILI['submission_week']  # noqa: E712
                                          == data_ILI['first_survey']), 'ILI'] = False
# correction for first submitted ARI survey ever
data_ILI.loc[(data_ILI['ARI'] == True) & (data_ILI['submission_week']  # noqa: E712
                                          == data_ILI['first_survey']), 'ARI'] = False


# Merge episodes

data_ILI = data_ILI.drop_duplicates(['participantID', 'onset_week'], keep='last')


weekly_ARI = {'onset_week': 0.0}
if data_ILI[(data_ILI['ARI'] == True)].shape[0] > 0:  # noqa: E712
    weekly_ARI = data_ILI[(data_ILI.ARI == True)].groupby('onset_week').size().to_dict()  # noqa: E712, E501
season_ARI = data_ILI[(data_ILI.ARI == True)].groupby('season').size()  # noqa: E712

active, ARI = 0, 0
incidence_ARI = {}

act_threshold = 100
rescaling = 1000
for week in sorted(submission_weeks):
    if week in weekly_ARI:
        active = weekly_active_user[week]
        ARI = weekly_ARI[week]
    else:
        ARI = 0
    if active > act_threshold and ARI > 0:
        incidence_ARI[week] = round(ARI * 1.0 / active * rescaling, 2)
    else:
        incidence_ARI[week] = 0

weekly_ILI = {'onset_week': 0.0}

if data_ILI[(data_ILI['ILI'] == True)].shape[0] > 0:  # noqa: E712
    weekly_ILI = data_ILI[(data_ILI.ILI == True)].groupby('onset_week').size().to_dict()  # noqa: E712, E501

active, ILI = 0, 0
incidence = {}
act_threshold = 100

for week in sorted(submission_weeks):
    active, ILI = 0, 0
    if week in weekly_ILI:
        active = weekly_active_user[week]
        ILI = weekly_ILI[week]
    else:
        ILI = 0
    if active > act_threshold and ILI > 0:
        incidence[week] = round(ILI * 1.0 / active * rescaling, 2)
    else:
        incidence[week] = 0

os.makedirs(output_dir, exist_ok=True)


def _gcs_write_csv(df_or_series, path, **kwargs):
    """Remove an existing GCS-FUSE file before writing; FUSE rejects in-place overwrites."""
    if os.path.exists(path):
        os.remove(path)
    df_or_series.to_csv(path, **kwargs)


# Drop sentinel first so the serving pod never reads partial data.
_ready_path = os.path.join(output_dir, '.READY')
if os.path.exists(_ready_path):
    os.remove(_ready_path)

# save epi values
_gcs_write_csv(
    pd.Series(incidence).to_frame('incidence'),
    os.path.join(
        output_dir,
        'ILI_incidence.csv'),
    header=True)
_gcs_write_csv(
    pd.Series(incidence_ARI).to_frame('incidence'),
    os.path.join(
        output_dir,
        'ARI_incidence.csv'),
    header=True)
_gcs_write_csv(
    pd.Series(wau).to_frame('active users'),
    os.path.join(
        output_dir,
        'active_users.csv'),
    header=True)

# save participants values
_gcs_write_csv(
    intake['gender'].value_counts(),
    os.path.join(
        output_dir,
        'gender.csv'),
    header=True)
_gcs_write_csv(
    intake['edu'].value_counts(),
    os.path.join(
        output_dir,
        'education.csv'),
    header=True)
_gcs_write_csv(
    intake['occupation'].value_counts(),
    os.path.join(
        output_dir,
        'occupation.csv'),
    header=True)
_gcs_write_csv(
    intake['age_class'].value_counts(),
    os.path.join(
        output_dir,
        'age.csv'),
    header=True)


# ## Mappa

pop_reg = pd.read_csv(os.path.join(_HERE, 'pop_reg.csv'), header=0, names=[
                      'regione', 'pop']).set_index('regione').squeeze()

regioni = gpd.read_file(
    os.path.join(
        _HERE,
        'Limiti01012024_g-2/Reg01012024_g/Reg01012024_g_WGS84.shp'))
regioni = regioni[['DEN_REG', 'geometry']].set_index('DEN_REG')

partecipanti_reg = data_ILI.reg.value_counts().to_frame('count')

part_reg = (
    intake.reg.value_counts().squeeze() /
    pop_reg *
    100000).reindex(
        list(
            regioni.index)).to_frame('count')

reg_map = regioni.join(part_reg).reset_index()
reg_map = reg_map[['DEN_REG', 'count', 'geometry']].set_index('DEN_REG')

ili_counts = data_ILI[data_ILI.ILI == True].reg.value_counts()  # noqa: E712
ar = (
    ili_counts /
    partecipanti_reg['count'] *
    100).reindex(
        list(
            regioni.index)).fillna(0).rename('ar').to_frame()


reg_map_ar = reg_map.join(ar, how='left').reindex(list(regioni.index)).fillna(0).reset_index()
_gcs_write_csv(reg_map_ar, os.path.join(output_dir, 'reg_map.csv'), index=False)

# add sentinel last so Plotting.py's @st.cache_data (keyed on
# this mtime) only invalidates once all outputs are complete.
with open(_ready_path, 'w') as f:
    f.write(datetime.datetime.now(datetime.timezone.utc).isoformat() + '\n')
