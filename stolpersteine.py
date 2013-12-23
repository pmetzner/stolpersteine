import pandas as pd
import numpy as np
import json
import urllib2
import datetime
import re
import time

data = pd.read_csv('./stolpersteine.csv')

## Sanitize time stamps and interpolate missing data

def todate(date):
    """If there is not data, assign the end of the war; if it's only"""
    if date!=date:
        date="1945-05-08"
    elif len(date)==4:
        date="%04d-01-01" % int(date)
    elif len(date) < 8 :
        date="%04d-%02d-01" % tuple([int(i) for i in date.split('/')[::-1]])
    else:
        date="%02d-%02d-%02d" % tuple([int(i) for i in date.split('/')[::-1]])
    date = datetime.date(*[int(i) for i in date.split("-")])
    return date

date_to_string = lambda x: x.strftime("%Y-%m-%d")

data['deport'] = data['Deportationstag'].map(todate)
data['death'] = data['Todestag'].map(todate)


## Calculate time offset from first deportation date
firstdate = data['deport'].min()
timestamp_offset = lambda x: (x - firstdate).days

data['timestamp'] = data['deport'].map(timestamp_offset)

## Translate addresses to coordinates (caveat: street names have probably in some instances)

def geocode(address):
    """Fetch coordinates for address via Google Geocoding API, return dictionary with coordinates"""
    address = re.sub(' ', '+', address) # Replace whitespace with '+' for URL
    address = address + ',+Berlin,+Germany'
    url = "http://maps.googleapis.com/maps/api/geocode/json?address=%s,+%s&sensor=true" % address
    response = urllib2.urlopen(url)
    try:
        coord = json.load(response)
        output = coord['results'][0]['geometry']['location']
    except ValueError:
        output = None
    time.sleep(0.5) # Google Geocoding API shuts you out if requests come to frequently
    return output

coords = {}
for address in data['Adresse'].unique():
    coords[address] = geocode(address)

data['lat'] = [coords[a]['lat'] for a in data['Adresse']]
data['lng'] = [coords[a]['lng'] for a in data['Adresse']]


data.sort(['deport', 'death'], inplace=True)

## Merge first name, last name (and optionally maiden name) into one string

for i in xrange(1,data.shape[0]):
    if pd.isnull(data['Nachname'][i-1]):
        data['name'][i-1] = data['Vorname'][i-1]
    elif pd.isnull(data['Geburtsname'][i-1]):
        data['name'][i-1] = data['Vorname'][i-1] + " " + data['Nachname'][i-1]
    else:
        data['name'][i-1] = data['Vorname'][i-1] + " " + data['Nachname'][i-1] + " (geb. " + data['Geburtsname'][i-1] + ")"

## Sanitize place of murder
output = data[['name', 'deport', 'death', 'timestamp', 'Todesort', 'lat', 'lng']]
output.columns = ['name', 'deport', 'death', 'timestamp', 'murder', 'lat', 'lng']

output.to_csv('./stolpersteine.tsv', sep = '\t', index = False)
