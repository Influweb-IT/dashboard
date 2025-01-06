import numpy as np
import geopandas as gpd
import pgeocode
import pandas as pd
from collections import Counter, defaultdict
import os, sys, glob, re, datetime
from datetime import date, timedelta

#Convert weeks with formats like 2014-2 to proper format 2014-02
def fix_yearweek(date_string):
    year, week =  map(lambda x: int(x), date_string.split('-'))
    fixed = "{0}-{1:02d}".format(year, week)
    
    assert re.match(r"\d{4}-\d{2}$", fixed)
    return fixed

def weekMinus(week, minusweek):
    #week is a string 'yyyy-w'
    yr, wk = map(lambda x: int(x), week.split('-'))
    mid_date = getMiddleDayOfWeek(yr, wk)
    res_date = mid_date - timedelta(days=7*minusweek)
    isoyear, isoweek, isoday = res_date.isocalendar()
    return str(isoyear) + '-' + str(isoweek)

def getMiddleDayOfWeek(year, week):
    d = datetime.date(year,1,1)
    if(d.weekday()>3):
        d = d+timedelta(7-d.weekday())
    else:
        d = d - timedelta(d.weekday())
    dlt = timedelta(days = (week-1)*7)
    return d + dlt + timedelta(days=3)

def weekPlusOne(week):
    #week is a string 'yyyy-w'
    yr, wk = map(lambda x: int(x), week.split('-'))
    mid_date = getMiddleDayOfWeek(yr, wk)
    res_date = mid_date + timedelta(days=7)
    isoyear, isoweek, isoday = res_date.isocalendar()
    return str(isoyear) + '-' + str(isoweek)

def days_difference(date1, date2):
    y1,m1,d1 = map(lambda x: int(x), date1.split('-'))
    y2,m2,d2 = map(lambda x: int(x), date2.split('-'))
    delta_days = (datetime.date(y1,m1,d1) - datetime.date(y2,m2,d2)).days
    return delta_days

def get_onset_date( submission_date, symptoms_date, fever_date ):
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
        while(wk <= wk_end):
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
    ILI=False
    if row.symptoms==True:
        if row['Sudden onset']==True or row['Sudden fever']==True: #0 = sudden onset
            if row.Fever==True or row.Chills==True or row['Malaise']==True or row.Headache==True or row['Muscle/joint pain']==True:
                if row['Sore throat']==True or row.Cough==True or row['Shortness of breath']==True:
                    ILI=True  
    return ILI

def get_ARI(row):
    ARI=False
    if row.symptoms==True:
        if row['Sudden onset']==0.0: #0 = sudden onset
            if row.Cough==True or row['Sore throat']==True or row['Shortness of breath']==True or row['Runny or blocked nose']==True:
                ARI=True  
    return ARI

###
# Return previous week (es: lastweek(datetime.datetime.strptime('18112019', "%d%m%Y").date()) -> 2019-46)
###
def lastweek(today=date.today()):
    for i in range(7):
        x = str((today - timedelta(days=i)).isocalendar()[0])+'-'+str((today - timedelta(days=i)).isocalendar()[1])
        d1 = str(today.isocalendar()[0])+'-'+str(today.isocalendar()[1])
        if x!=d1:
              return fix_yearweek(x)

def unite(x):
    #print(x)
    aa=np.where(x)[0]
    if len(aa)>0:
        return int(aa[0])
        print(aa)
    else: return np.nan
    
    
def translate(entry):
    if entry=='f':
        entry=False
    elif entry=='FALSE':
        entry=False
    elif entry=='t':
        entry=True
    elif entry=='TRUE':
        entry=True
    return entry

def get_age(unix_timestamp):
    """Given a unix timestamp as date of birth, return the age in years."""
    if pd.notnull(unix_timestamp):
        dob = datetime.datetime.fromtimestamp(unix_timestamp)
        today = datetime.datetime.now()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    else:
        return np.nan
        
def get_age_class(x):
    if x<18 and x>0:
        return '<18'
    elif x>=18 and x<=40:
        return '18-40'
    elif x>40 and x<=65:
        return '41-65'
    elif x>65:
        return '>65'
    else: return 'nan'

def occupation(x):
    if x['intake.Q4-rg.scg.0']:
        return 'full_time'
    elif x['intake.Q4-rg.scg.1']:
        return 'part_time'
    elif x['intake.Q4-rg.scg.2']:
        return 'self-employed'
    elif x['intake.Q4-rg.scg.3']:
        return 'student'
    elif x['intake.Q4-rg.scg.4']:
        return 'homemaker'
    elif x['intake.Q4-rg.scg.5']:
        return 'unemployed'
    elif x['intake.Q4-rg.scg.6']:
        return 'on leave'
    elif x['intake.Q4-rg.scg.7']:
        return 'retired'
    elif x['intake.Q4-rg.scg.8']:
        return 'other'
    
    
def schooling(x):
    if x['intake.Q4d-rg.scg.0']:
        return 'none'
    elif x['intake.Q4d-rg.scg.11']:
        return 'int_school'
    elif (x['intake.Q4d-rg.scg.12'] or x['intake.Q4d-rg.scg.13']):
        return 'high_school'
    elif x['intake.Q4d-rg.scg.3']:
        return 'bachelor'
    elif x['intake.Q4d-rg.scg.4']:
        return 'master_phd'
    elif x['intake.Q4d-rg.scg.5']:
        return 'other'
    
def get_edu(x):
    if str(x)=='None' or str(x)=='none' or x==np.nan or x=='student':
        return 'elementary'
    elif x=='int_school' or x=='high_school':
        return 'secondary'
    elif x=='master_phd' or x=='bachelor':
        return 'higher'
    elif x=='other':
        return 'other'

def change_regname(x):
    if x=='Emilia-Romagna':
        return 'Emilia-Romagna' 
    elif x=="Valle d'Aosta/Vallée d'Aoste":
        return "Valle d'Aosta"
    elif x=="Valle d'Aosta / Vallée d'Aoste":
        return "Valle d'Aosta"
    elif x=='Trentino-Alto Adige/Südtirol':
        return 'Trentino-Alto Adige'
    elif x=='Trentino-Alto Adige / Südtirol':
        return 'Trentino-Alto Adige'
    elif x=='Trentino Alto Adige / Südtirol':
        return 'Trentino-Alto Adige'
    elif x=='Abruzzi':
        return 'Abruzzo'
    elif x=="Valle D'Aosta":
        return "Valle d'Aosta"
    else: return x


def get_province(postal_code):
    if postal_code == 'False':
        return 'Unknown'
    postal_code = int(postal_code)
    if 1000 <= postal_code <= 1299:
        return 'Bruxelles'
    elif 1300 <= postal_code <= 1499:
        return 'Brabant Wallon'
    elif (1500 <= postal_code <= 1999) or (3000 <= postal_code <= 3499):
        return 'Vlaams-Brabant'
    elif 2000 <= postal_code <= 2999:
        return 'Antwerpen'
    elif 3500 <= postal_code <= 3999:
        return 'Limburg'
    elif 4000 <= postal_code <= 4999:
        return 'Liège'
    elif 5000 <= postal_code <= 5999:
        return 'Namur'
    elif (6000 <= postal_code <= 6599) or (7000 <= postal_code <= 7999):
        return 'Hainaut'
    elif 6600 <= postal_code <= 6999:
        return 'Luxembourg'
    elif 8000 <= postal_code <= 8999:   
        return 'West-Vlaanderen'
    elif 9000 <= postal_code <= 9999:
        return 'Oost-Vlaanderen'
    else:
        return 'Unknown'

YEAR_MIN, YEAR_MAX = 2023, 2024

dates = datetime.date.today()

last_week = lastweek(dates)

my_yearweek = last_week
min_year = str(YEAR_MIN)
max_year = str(YEAR_MAX)
previous_season = str(int(max_year)-2)+'-'+str(int(max_year)-1)
first_day = min_year+'-11-01' # from Nov 1stM
last_day = max_year+'-05-01' # to May 1st
print(f"Min year: {min_year}, Max year: {max_year}, Prev season: {previous_season}")
print(f"First day: {first_day}, Last day: {last_day}")

# CALENDAR
delta = timedelta(days=1)
curr, end = datetime.date(YEAR_MIN, 11, 1), datetime.date.today() #datetime.date(YEAR_MAX, 5, 1)
date_week = dict()
llyearweek, week_to_consider = [], []
while curr <= end:
    yearweek = fix_yearweek( str(curr.isocalendar()[0])+'-'+str(curr.isocalendar()[1]) )
    date = curr.isoformat()
    date_week[date] = yearweek
    if date >= first_day and date <= last_day:
        if yearweek<=my_yearweek and yearweek not in week_to_consider:
            week_to_consider.append(yearweek)
        if yearweek not in llyearweek:
            llyearweek.append(yearweek)
    curr+=delta

date_season = dict()
season_week = defaultdict(set)
week_season = {}

for yr_min in range(YEAR_MIN, YEAR_MAX, 1):
    yr_max = yr_min+1
    for date in date_week.keys():
        from_ = datetime.date(yr_min, 11, 1).isoformat()
        to_ = datetime.date(yr_max, 5, 1).isoformat()
        if str(yr_min)+'-11-01'<= date <= str(yr_max)+'-05-01' :
            season = str(yr_min)+'-'+str(yr_max)
            date_season[date] = season
            date_f = datetime.datetime.strptime(str(date),'%Y-%m-%d')
            weeknr=str(date_f.isocalendar().year)+'-'+str(date_f.isocalendar().week).zfill(2)
            season_week[season].add(weeknr)
            week_season[weeknr]=season

seasons = set(season_week.keys())

date_season = dict()
for yr_min in range(YEAR_MIN, YEAR_MAX, 1):
    yr_max = yr_min+1
    for date in date_week.keys():
        from_ = datetime.date(yr_min, 11, 1).isoformat()
        to_ = datetime.date(yr_max, 5, 1).isoformat()
        if str(yr_min)+'-11-01'<= date <= str(yr_max)+'-05-01' :
            season = str(yr_min)+'-'+str(yr_max)
            date_season[date] = season


# In[241]:


path = './data/raw/intake/'
os.makedirs(path, exist_ok=True)

dfs = []
for filename in glob.glob(path+'*.csv'):
    with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode
        # do your stuff
        dfs.append(pd.read_csv(f))

intake_complete = pd.concat(dfs)

############
## INTAKE ##
############

intake_complete['timestamp'] = intake_complete.submittedAt.apply(lambda d: pd.to_datetime(int(d),unit='s'))
intake_complete.timestamp = pd.to_datetime(intake_complete.timestamp, utc=True).apply(lambda d: d.strftime('%Y-%m-%d %H:%M:%S'))
intake_complete = intake_complete.sort_values("timestamp", ascending=True)

# some cleaning:

# remove surveys with no global_id , if any
intake_complete = intake_complete[pd.isnull(intake_complete.participantID)==False]

# rename cols
intake_complete.rename(columns={'intake.Q3-rg.scg.0':'postal_code', 'timestamp': 'intake_timestamp'}, inplace=True)
intake_complete.drop_duplicates('intake_timestamp', keep='last', inplace=True)

# add date, province and vaccine
intake_complete.insert(4, "intake_submission", intake_complete.intake_timestamp.str.split().str[0])

#gender
intake_complete['gender'] = intake_complete.apply(lambda row: 'Male' if row['intake.Q1-rg.scg.0']==True else 'Female' if row['intake.Q1-rg.scg.1']==True else 'Other', axis=1)

#age
intake_complete['age'] = intake_complete['intake.Q2-rg.1'].apply(lambda x: get_age(x))
intake_complete['age_class'] = intake_complete[['age']].map(lambda x: get_age_class(x))

#province
intake_complete['reg'] = intake_complete['postal_code'].apply(lambda x: get_province(x))

# add occupation and education degree
# df.apply didnt like this structure, improvements later?
for i, row in intake_complete.iterrows():
        if row['intake.Q4-rg.scg.0']:
            intake_complete.loc[i, 'occupation'] = 'full_time'
        elif row['intake.Q4-rg.scg.1']:
            intake_complete.loc[i, 'occupation'] = 'part_time'
        elif row['intake.Q4-rg.scg.2']:
            intake_complete.loc[i, 'occupation'] = 'self-employed'
        elif row['intake.Q4-rg.scg.3']:
            intake_complete.loc[i, 'occupation'] = 'student'
        elif row['intake.Q4-rg.scg.4']:
            intake_complete.loc[i, 'occupation'] = 'homemaker'
        elif row['intake.Q4-rg.scg.5']:
            intake_complete.loc[i, 'occupation'] = 'unemployed'
        elif row['intake.Q4-rg.scg.6']:
            intake_complete.loc[i, 'occupation'] = 'on leave'
        elif row['intake.Q4-rg.scg.7']:
            intake_complete.loc[i, 'occupation'] = 'retired'
        elif row['intake.Q4-rg.scg.8']:
            intake_complete.loc[i, 'occupation'] = 'other'
    
for i, row in intake_complete.iterrows():
    if row['intake.Q4d-rg.scg.0']:
        intake_complete.loc[i, 'edu'] =  'none'
    elif row['intake.Q4d-rg.scg.11']:
        intake_complete.loc[i, 'edu'] =  'int_school'
    elif (row['intake.Q4d-rg.scg.12'] or row['intake.Q4d-rg.scg.13']):
        intake_complete.loc[i, 'edu'] =  'high_school'
    elif row['intake.Q4d-rg.scg.3']:
        intake_complete.loc[i, 'edu'] =  'bachelor'
    elif row['intake.Q4d-rg.scg.4']:
        intake_complete.loc[i, 'edu'] =  'master_phd'
    elif row['intake.Q4d-rg.scg.5']:
        intake_complete.loc[i, 'edu'] =  'other'

intake_complete['education'] = intake_complete['edu'].apply(lambda x: get_edu(x))

intake_complete = intake_complete[intake_complete.age_class!='nan']

intake = intake_complete[["participantID","age_class","gender","reg","edu","occupation","intake_timestamp","intake_submission"]]

# intermediary save to check
# intake.to_csv('./data/output/intake-clean.csv', index=False)

path = './data/raw/weekly/'
os.makedirs(path, exist_ok=True)

dfs = []

for filename in glob.glob(path+'*.csv'):
    with open(os.path.join(os.getcwd(), filename), 'r') as f: # open in readonly mode
        # do your stuff
        dfs.append(pd.read_csv(f))

weekly_complete = pd.concat(dfs)


############
## WEEKLY ##
############

def transf_date(x):
    if str(x) == 'False' or str(x) == 'True':
        # print('Transform date warning: boolean input')
        return ''
    if pd.notnull(x):
        newx = pd.to_datetime(int(x),unit='s')
        return newx
    else:
        return ''
    
weekly_complete['weekly.HS.Q3.0'] = weekly_complete['weekly.HS.Q3-rg.0'].apply(lambda d: transf_date(d))
weekly_complete['weekly.HS.Q4.0'] = weekly_complete['weekly.HS.Q4-rg.scg.0'].apply(lambda d: transf_date(d))
weekly_complete['weekly.HS.Q6.1'] = weekly_complete['weekly.HS.Q6.a-rg.scg.1'].apply(lambda d: transf_date(d))

weekly_complete['timestamp'] = weekly_complete.submittedAt.apply(lambda d: pd.to_datetime(int(d),unit='s', errors = 'coerce'))
weekly_complete.timestamp = pd.to_datetime(weekly_complete.timestamp, utc=True).apply(lambda d: d.strftime('%Y-%m-%d %H:%M:%S'))
weekly_complete = weekly_complete.sort_values("timestamp", ascending=True)
weekly_complete = weekly_complete[weekly_complete.timestamp <= dates.strftime('%Y-%m-%d %H:%M:%S')]


weekly_complete['weekly.HS.Q3.0'] = pd.to_datetime(weekly_complete['weekly.HS.Q3.0'], utc=True, errors='coerce').dt.strftime('%Y-%m-%d')
weekly_complete['weekly.HS.Q4.0'] = pd.to_datetime(weekly_complete['weekly.HS.Q4.0'], utc=True, errors='coerce').dt.strftime('%Y-%m-%d')
weekly_complete['weekly.HS.Q6.1'] = pd.to_datetime(weekly_complete['weekly.HS.Q6.1'], utc=True, errors='coerce').dt.strftime('%Y-%m-%d')

weekly_complete['Sudden onset']= weekly_complete['weekly.HS.Q5-rg.scg.0'].apply(lambda x: True if x==0 else False)
weekly_complete['Sudden fever']= weekly_complete['weekly.HS.Q6.b-rg.scg.1'].apply(lambda x: True if x==0 else False)

#homogenize true and false
#weekly_complete[weekly_complete.filter(regex='(^Q[1,7,8,9]+_+[0-9]+$)',axis=1).columns] = weekly_complete[weekly_complete.filter(regex='(^Q[1,7,8,9]+_+[0-9]+$)',axis=1).columns].isin(["True", "t",True])
weekly_complete[['Q1_0','Fever','Chills','Runny or blocked nose','Sneezing','Sore throat','Cough','Shortness of breath','Headache',
                 'Muscle/joint pain','Chest pain','Malaise','Loss of appetite','Coloured sputum','Watery, bloodshot eyes'
                 ,'Nausea','Vomiting','Diarrhoea','Stomach ache','Other','Rash','Loss of taste', 'Nose bleed', 'Loss of smell', 'Confusion']]= weekly_complete[['weekly.Q_BE_1-rg.mcg.0',
'weekly.Q_BE_1-rg.mcg.1','weekly.Q_BE_1-rg.mcg.2','weekly.Q_BE_1-rg.mcg.3','weekly.Q_BE_1-rg.mcg.4','weekly.Q_BE_1-rg.mcg.5','weekly.Q_BE_1-rg.mcg.6','weekly.Q_BE_1-rg.mcg.7','weekly.Q_BE_1-rg.mcg.8',
'weekly.Q_BE_1-rg.mcg.9','weekly.Q_BE_1-rg.mcg.10', 'weekly.Q_BE_1-rg.mcg.11', 'weekly.Q_BE_1-rg.mcg.12','weekly.Q_BE_1-rg.mcg.13', 'weekly.Q_BE_1-rg.mcg.14','weekly.Q_BE_1-rg.mcg.15','weekly.Q_BE_1-rg.mcg.16',
'weekly.Q_BE_1-rg.mcg.17','weekly.Q_BE_1-rg.mcg.18','weekly.Q_BE_1-rg.mcg.19','weekly.Q_BE_1-rg.mcg.20','weekly.Q_BE_1-rg.mcg.21','weekly.Q_BE_1-rg.mcg.22','weekly.Q_BE_1-rg.mcg.23', 'weekly.Q_BE_1-rg.mcg.24']].map(lambda x: translate(x))

# some cleaning:
# remove surveys with no global_id, if any, and consider only surveys which have a corresponding intake survey
weekly_complete = weekly_complete[pd.isnull(weekly_complete.participantID)==False]
weekly_complete = weekly_complete[weekly_complete.participantID.isin(intake.participantID.unique())]

# add cols
weekly_complete.rename(columns={'timestamp': 'weekly_timestamp'}, inplace=True)
weekly_complete.insert(3, "submission_date", weekly_complete.weekly_timestamp.str.split().str[0])
weekly_complete.insert(4, "submission_week", weekly_complete.submission_date.map(date_week))
weekly_complete.insert(5, "season", weekly_complete.submission_date.map(date_season))

#keep only current season
weekly_complete = weekly_complete[weekly_complete.season =='2023-2024']

# remove duplicates within the same week, keeping the last one
weekly = weekly_complete.drop_duplicates(['participantID','submission_week'], keep='last', inplace=False)


# keep only the following columns
columns_to_keep_weekly = ['participantID', 'weekly_timestamp', 'submission_date', 'submission_week', 'season', 
                          'weekly.HS.Q3.0', 'weekly.HS.Q4.0', 'weekly.HS.Q6.1', 'Sudden onset', 'Sudden fever',
                          'Q1_0','Fever','Chills','Runny or blocked nose','Sneezing','Sore throat','Cough','Shortness of breath','Headache',
                          'Muscle/joint pain','Chest pain','Malaise','Loss of appetite','Coloured sputum','Watery, bloodshot eyes',
                          'Nausea','Vomiting','Diarrhoea','Stomach ache','Other','Rash','Loss of taste', 'Nose bleed', 'Loss of smell', 'Confusion']

weekly = weekly[columns_to_keep_weekly]

# intermediary save to check
# weekly.to_csv('./data/output/weekly-clean.csv', index=False)

#####################
## WEEKLY + INTAKE ##
#####################
# Merge weekly and intake according to the most recent intake per each weekly_survey submitted
frames = []
for item, group in weekly.groupby(["participantID","weekly_timestamp","submission_date"]):
    participantID, weekly_timestamp, submission_date = item
    intake_timestamp = intake[(intake.participantID==participantID) & (intake.intake_timestamp<=weekly_timestamp)].intake_timestamp.max()
    frames.append({'participantID': participantID, 'submission_date':submission_date, 'intake_timestamp':intake_timestamp})
data = weekly.merge(pd.DataFrame(frames), on=["participantID", "submission_date"], how="left")
data = data.merge(intake, on=["participantID", "intake_timestamp"], how="left")
assert(data.shape[0]==weekly.shape[0])


all_weeks = sorted(set(data.submission_week.dropna().values)) #all weeks in the period
real_weeks = sorted(set(week_season.keys())) #only weeks in seasons

data = data[~pd.isna(data.season)]


# ACTIVE USERS (in real-time):
# - AT LEAST 2 symptoms surveys
# - WINDOW OF PARTICIPATION: +/- 2 WEEKS AROUND THE WEEK OF REPORTING

# keep only surveys of participants who submitted >= 2 symptoms surveys
data = data.groupby('participantID').filter(lambda x: len(x)>1)
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
all_symptoms = ['Fever','Chills','Runny or blocked nose','Sneezing','Sore throat','Cough','Shortness of breath','Headache',
                 'Muscle/joint pain','Chest pain','Malaise','Loss of appetite','Coloured sputum','Watery, bloodshot eyes'
                 ,'Nausea','Vomiting','Diarrhoea','Stomach ache','Other','Rash','Loss of taste', 'Nose bleed', 'Loss of smell','Sudden onset','Sudden fever']

all_weeks_tf = [yearweek_to_ts(x) for x in all_weeks]
real_weeks_tf= [yearweek_to_ts(x) for x in real_weeks]


data_ILI = data.copy(deep=True)
data_ILI = data_ILI[ data_ILI.season.isin(seasons) ] #get only weeks in seasons

ILI_weeks=set(data_ILI.submission_week)
submission_weeks=[x for x in list(week_season.keys()) if x<='2024-18'] #ILI_weeks

data_ILI['symptoms'] = data_ILI['Q1_0'].apply(lambda x: False if x==True else True)

####################
## Merge episodes ##
####################

# define first_survey ever for each user
data_ILI['first_survey'] = data_ILI.groupby(['participantID'])['submission_week'].transform('min')

data_ILI['ILI'] = data_ILI.apply(lambda row: get_ILI_ECDC(row), axis=1)
data_ILI['ARI'] = data_ILI.apply(lambda row: get_ARI(row), axis=1)

#define onset week based on reported onset or reported fever onset for ILI and ARI only
data_ILI['onset_week'] = data_ILI.apply(lambda row: get_onset_date(row.submission_date, row['weekly.HS.Q3.0'], row['weekly.HS.Q6.1']) if any([row['ILI']==True,row['ARI']==True]) else np.nan, axis=1).map(date_week) # only if ILI or ARI

##############################
## Remove first submissions ##
##############################

#correction for first submitted ILI survey ever
data_ILI.loc[(data_ILI['ILI']==True) & (data_ILI['submission_week']==data_ILI['first_survey']), 'ILI']= False
#correction for first submitted ARI survey ever
data_ILI.loc[(data_ILI['ARI']==True) & (data_ILI['submission_week']==data_ILI['first_survey']), 'ARI']= False


####################
## Merge episodes ##
####################

data_ILI = data_ILI.drop_duplicates(['participantID','onset_week'], keep='last')


weekly_ARI = {'onset_week':0.0}
if data_ILI[(data_ILI['ARI']==True)].shape[0]>0:
    weekly_ARI = data_ILI[(data_ILI.ARI==True)].groupby('onset_week').size().to_dict()
season_ARI = data_ILI[(data_ILI.ARI==True)].groupby('season').size()

active, ARI = 0, 0
incidence_ARI = {}

act_threshold=100
rescaling=1000
for week in sorted(submission_weeks):
    if week in weekly_ARI:
        active = weekly_active_user[week]
        ARI = weekly_ARI[week]
    else: ARI = 0
    if active>act_threshold and ARI>0:
        incidence_ARI[week] = round( ARI*1.0/active*rescaling, 2 )
    else: incidence_ARI[week] = 0

weekly_ILI = {'onset_week':0.0}

if data_ILI[(data_ILI['ILI']==True)].shape[0]>0:
    weekly_ILI = data_ILI[(data_ILI.ILI==True)].groupby('onset_week').size().to_dict()
    
active, ILI = 0, 0
incidence = {}
act_threshold = 100

for week in sorted(submission_weeks):
    active, ILI = 0, 0
    if week in weekly_ILI:
        active = weekly_active_user[week]
        ILI = weekly_ILI[week]
    else: ILI = 0
    if active>act_threshold and ILI>0:
        incidence[week] = round( ILI*1.0/active*rescaling, 2 )
    else: incidence[week] = 0

output_dir = './data/dashboard/'
os.makedirs(output_dir, exist_ok=True)

## Save epi values
pd.Series(incidence).to_frame('incidence').to_csv(os.path.join(output_dir, 'ILI_incidence.csv'), header=True)
pd.Series(incidence_ARI).to_frame('incidence').to_csv(os.path.join(output_dir, 'ARI_incidence.csv'), header=True)
pd.Series(wau).to_frame('active users').to_csv(os.path.join(output_dir, 'active_users.csv'), header=True)

#save participants values
intake['gender'].value_counts().to_csv(os.path.join(output_dir, 'gender.csv'), header=True)
intake['edu'].value_counts().to_csv(os.path.join(output_dir, 'education.csv'), header=True)
intake['occupation'].value_counts().to_csv(os.path.join(output_dir, 'occupation.csv'), header=True)
intake['age_class'].value_counts().to_csv(os.path.join(output_dir, 'age.csv'), header=True)


## Map

pop_reg = pd.read_csv('pop_reg.csv',header=0, names=['regione','pop']).set_index('regione').squeeze()

region = gpd.read_file('shapefiles/belgium/belgium.shp')
region = region[['NAME_2','geometry']].set_index('NAME_2')

partecipanti_reg = data_ILI.reg.value_counts().squeeze().reset_index().set_index('reg')

part_reg = intake.reg.value_counts().squeeze()/pop_reg * 100000
part_reg = part_reg.reindex(list(region.index))
part_reg = part_reg.reset_index().set_index('index')

reg_map = region.join(part_reg).reset_index().rename(columns={0:'count'})
reg_map = reg_map[['NAME_2','count','geometry']].set_index('NAME_2')

ar = ((data_ILI[data_ILI.ILI==True].reg.value_counts().reset_index().set_index('reg')/partecipanti_reg).reindex(list(region.index)).fillna(0)*100)
ar = ar.reset_index().set_index('reg').rename(columns={'count':'ar'})


reg_map_ar = reg_map.join(ar,how='left').reindex(list(region.index)).fillna(0).reset_index()
reg_map_ar.to_csv(os.path.join(output_dir, 'reg_map.csv'), index=False)
