# dataRunner.py

dataRunner is a framework that allows for easy retrieval of user data from the Fitbit API. Functions include the ability 
to request user access, store credentials needed for later retrieval, and query summary and intraday information. The 
framework currently exists as a single Python script with functions. *Currently in development.*


## To Do
- Fitbit Client
    - migrate to Oauth 2.0
    - write function to retrieve and store heart rate details
    - rewrite intraday retrieval function to output a single csv with all intraday activities for each user
    - rewrite intraday retrieval function to accept a range of dates for output
    - write function to retrieve and store details of a particular activity (bike ride, jog, etc.)
    - write function to retrieve and store earned badges
    - write function to retrieve and store sleep data
    - write function to retrieve and store list of friends
- To the web
    - port existing code to a web framework that allows for easy online access and sign up
- Add additional clients
    - Nike+
    - Jawbone
    - Apple Healthkit
    - Garmin
    - Google Fit

## Dependencies
- fitbit
- tqdm
- selenium
- pymongo