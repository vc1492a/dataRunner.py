import fitbit
import configparser
from contextlib import closing
from selenium.webdriver import Firefox
from selenium.webdriver.support.ui import WebDriverWait
import json
import csv
from tqdm import tqdm
from pymongo import MongoClient
try:
    # Python 3
    from urllib.parse import urlparse, parse_qs
except ImportError:
    # Python 2
    from urlparse import urlparse, parse_qs

# initialize mongodb
mongo_client = MongoClient()
user_db = mongo_client['user']
credentials = user_db['credentials'] # stores user credentials
user_profiles = user_db['user_profiles'] # stores user profiles and demographic information
activity_data_intraday = user_db['activity_data_intraday'] # stores intraday values
activity_lifetime = user_db['activity_lifetime'] # stores totals and best values; total and highest steps, floors, etc

# load settings
config = configparser.ConfigParser()
config.read('config.ini')
consumer_key = config.get('Login Parameters', 'C_KEY')
consumer_secret = config.get('Login Parameters', 'C_SECRET')


# AUTHORIZING ACCESS #


def authorized_access(key, secret):
    client = fitbit.FitbitOauthClient(key, secret)
    consumer_token = client.fetch_request_token()
    print('consumer key: %s' % str(consumer_token['oauth_token']))
    print('consumer secret: %s' % str(consumer_token['oauth_token_secret']))
    url = client.authorize_token_url()
    with closing(Firefox()) as browser:
        browser.get(url)
        button = browser.find_element_by_id('oauth_allow')
        button.click()
        # wait for the page to load
        WebDriverWait(browser, timeout=60).until(
            lambda x: x.find_element_by_id('wrapper'))
        # store it to string variable
        page_source = browser.current_url
    parsed_url = urlparse(page_source)
    query = str(parsed_url[4])
    query_split = query.split('=')
    oauth_verifier = query_split[2]
    print('verifier: %s' % str(oauth_verifier))
    user_token = client.fetch_access_token(oauth_verifier)
    print('user key: %s' % str(user_token['oauth_token']))
    print('user secret: %s' % str(user_token['oauth_token_secret']))
    print('user ID: %s' % str(user_token['encoded_user_id']))
    user_id = user_token['encoded_user_id']
    if credentials.find({'encoded_user_id': user_id}).count() == 0:
        insert_id = credentials.insert_one(user_token).inserted_id
    else:
        print('\nUser ID ' + user_id + ' already stored.\n')

# authorized_access(consumer_key, consumer_secret)

all_activities = ['activities/steps', 'activities/floors', 'activities/calories', 'activities/distance']


# INTRADAY ACTIVITY #


# REWRITE TO INCLUDE A UNIQUE ENTRY FOR EACH ACTIVITY FOR A SPECIFIED RANGE OF DATES #
def fetch_store_intraday(key, secret, activity, base_date, s_time, e_time, level):
    insert_array = []
    activity_split = activity.split('/')
    print('\n' + activity_split[1])
    activity_restring = 'activities-' + activity_split[1]
    for tokens, secrets, user_id in zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id')):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        intraday = authd_client.intraday_time_series(activity, base_date=base_date, detail_level=level, start_time=s_time, end_time=e_time)
        intraday['encoded_user_id'] = user_id
        if activity_data_intraday.find({'encoded_user_id': user_id, activity_restring: {"$exists": True}}).count() == 0:
            insert_array.append(intraday)
            print('User ' + user_id + ' added to database.')
        else:
            print('User ' + user_id + ' activity already stored.')
    if len(insert_array) != 0:
        activity_data_intraday.insert_many(insert_array)


def fetch_activities_intraday(activity_array, date, interval, key, secret):
    for types in activity_array:
        fetch_store_intraday(key, secret, types, date, None, None, interval)
    print('\n' + str(credentials.count()) + ' documents in credentials.')
    print(str(activity_data_intraday.count()) + ' documents in activity_data.')

# fetch_activities_intraday(all_activities, '2016-03-20', '1min', consumer_key, consumer_secret)


# PROFILES AND DEMOGRAPHICS #


def fetch_store_user_profile(key, secret):
    insert_array = []
    for tokens, secrets, user_id in zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id')):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        profile = authd_client.user_profile_get(user_id)
        profile['encoded_user_id'] = user_id
        if user_profiles.find({'encoded_user_id': user_id}).count() == 0:
            insert_array.append(profile)
            print('User ' + user_id + ' added to database.')
        else:
            print('User ' + user_id + ' activity already stored.')
    if len(insert_array) != 0:
        user_profiles.insert_many(insert_array)


def fetch_user_profiles(key, secret):
    fetch_store_user_profile(key, secret)
    print('\n' + str(credentials.count()) + ' documents in credentials.')
    print(str(user_profiles.count()) + ' documents in user_profiles.')

# fetch_user_profiles(consumer_key, consumer_secret)


def fetch_store_activity_lifetime(key, secret):
    insert_array = []
    for tokens, secrets, user_id in zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id')):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        lifetime = authd_client.activity_stats(user_id)
        lifetime['encoded_user_id'] = user_id
        if activity_lifetime.find({'encoded_user_id': user_id}).count() == 0:
            insert_array.append(lifetime)
            print('User ' + user_id + ' added to database.')
        else:
            print('User ' + user_id + ' activity already stored.')
    if len(insert_array) != 0:
        activity_lifetime.insert_many(insert_array)


def fetch_activity_lifetime(key, secret):
    fetch_store_activity_lifetime(key, secret)
    print('\n' + str(credentials.count()) + ' documents in credentials.')
    print(str(user_profiles.count()) + ' documents in activity_lifetime.')

# fetch_activity_lifetime(consumer_key, consumer_secret)


# DATA EXPORT FUNCTIONS #


def mongo_to_json(file_path, activity, collection):
    with open(file_path, 'w') as f:
        for user_id, activity in tqdm(zip(collection.distinct('encoded_user_id'), collection.distinct(activity))):
            data = collection.find_one({'encoded_user_id': user_id})
            data['_id'] = str(data['_id'])
            print(user_id)
            json.dump(data, f)
    f.close()

# mongo_to_json('output/dump.json', 'activities-steps', 'activity_data_intraday')


def mongo_to_csv_summary(file_path):
    with open(file_path, 'w') as f:
        writer = csv.writer(f)
        count = 0
        for doc in user_profiles.find({'encoded_user_id': {"$exists": True}}):
            user_profile_items = doc['user']
            user_profile_items.pop("topBadges", None)
            user_keys = sorted(user_profile_items.keys())
            if count == 0:
                header = list(doc.keys())
                header.remove('_id')
                header.remove('user')
                header.extend(user_keys)
                writer.writerow(header)
            count += 1
            encoded_user_id = doc['encoded_user_id']
            items = []
            row = []
            for i in user_keys:
                items.append(user_profile_items[i])
            row.append(encoded_user_id)
            for i in items:
                row.append(i)
            writer.writerow(row)
    f.close()

# mongo_to_csv_summary('data_export/test.csv')


# REWRITE TO INCLUDE ALL ACTIVITIES IN ONE CSV, AND TO INCLUDE A RANGE OF DATES #
def mongo_to_csv_intraday(file_path, activity_array):
    for activity in activity_array:
        activity_split = activity.split('/')
        activity_restring = 'activities-' + activity_split[1]
        activity_restring_intraday = 'activities-' + activity_split[1] + '-intraday'
        file_path_activity = file_path + 'intraday-' + activity_split[1] + '.csv'
        with open(file_path_activity, 'w') as f:
            writer = csv.writer(f)
            count = 0
            for doc in tqdm(activity_data_intraday.find({activity_restring: {"$exists": True}})):
                if count == 0:
                    header = list(doc.keys())
                    header.append('time')
                    header.remove('_id')
                    header.remove('activities-' + activity_split[1])
                    writer.writerow(sorted(header))
                count += 1
                # mongo_id = str(doc['_id'])
                encoded_user_id = doc['encoded_user_id']
                # day_activity = doc[activity_restring][0]['value']
                intraday_items = doc[activity_restring_intraday]['dataset']
                for i in range(0, len(intraday_items)):
                    row = []
                    # row.append(mongo_id)
                    # row.append(day_activity)
                    row.append(intraday_items[i]['value'])
                    row.append(encoded_user_id)
                    row.append(intraday_items[i]['time'])
                    writer.writerow(row)
        f.close()

# mongo_to_csv_intraday('data_export/', all_activities)


# EXPERIMENTAL FUNCTIONS #


def fetch_store_activity_detail(key, secret, activity_id):
    for tokens, secrets, user_id in tqdm(zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id'))):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        activity_detail = authd_client.activity_detail(activity_id)
        print(activity_detail)
        # NEEDS MONGO INTEGRATION #

# fetch_store_activity_detail(consumer_key, consumer_secret, '') # see activities.txt for list of activities


def fetch_store_activity_earned_badges(key, secret):
    for tokens, secrets, user_id in tqdm(zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id'))):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        badges = authd_client.get_badges(user_id)
        print(badges)
        # NEEDS MONGO INTEGRATION #

# fetch_store_activity_earned_badges(consumer_key, consumer_secret)


def fetch_store_sleep(key, secret, date):
    for tokens, secrets, user_id in tqdm(zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id'))):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        sleep = authd_client.get_sleep(date)
        print(sleep)
        # NEEDS MONGO INTEGRATION #

# fetch_store_sleep(consumer_secret, consumer_secret, '2016-03-20')


def fetch_store_user_friends(key, secret):
    for tokens, secrets, user_id in tqdm(zip(credentials.distinct('oauth_token'), credentials.distinct('oauth_token_secret'), credentials.distinct('encoded_user_id'))):
        authd_client = fitbit.Fitbit(key, secret, resource_owner_key=tokens, resource_owner_secret=secrets)
        friends = authd_client.get_friends(user_id)
        print(friends)
        # NEEDS MONGO INTEGRATION #

# fetch_store_user_friends(consumer_key, consumer_secret)
