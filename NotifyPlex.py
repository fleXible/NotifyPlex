#!/usr/bin/env python2
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Process to Update Plex Library and Notify PHT.
#
# This script sends a Targeted Library Update URL to your Plex Media Server and a GUI Notification to Plex Home Theater.
# Auto-Detection of NZBGet Category and Plex Sections is now supported.
#
# Copyright (C) 2014 mannibis
# Version 2.1.2
#
#
# NOTE: This script requires Python 2.x to be installed on your system.

##############################################################################
### OPTIONS                                                                ###

## General

# Refresh Plex Library (yes,no).
#
# Activate if you want NotifyPlex to Refresh your Plex Library
#refreshLibrary=yes

# Send GUI Notification to Plex Home Theater (yes,no).
#
# Activate if you want NotifyPlex to Send a GUI Notification to Plex Home Theater
#guiShow=yes

# Use Direct NZB Proper Name for Notification (yes,no).
#
# Activate if you want to use the DNZB Header ProperName for the title of the Media if Available
#dHeaders=yes

## Plex Media Server

# Plex Media Server Settings.
#
# Host IP of your Plex Media Server including Port (Only 1 Server is Supported)
#plexIP=192.168.1.XXX:32400

# Plex.tv Username [Required]
#plexUser=
# Plex.tv Password [Required]
#plexPass=

# Library Refresh Mode (Auto,Custom,Both).
#
# Select Refresh Mode: Auto will automatically detect your NZBGet Category and Refresh the Appropriate Sections, Custom will only refresh the Sections you input into the Custom Sections setting below, Both will Auto-detect and Refresh the Custom Sections
#refreshMode=Auto

# NZBGet Movies Category/Categories [Required for Auto Mode].
#
# List the name(s) of your NZBGet categories (CategoryX.Name) that correspond to Movies (Comma Separated)
#moviesCat=movies

# NZBGet TV Category/Categories [Required for Auto Mode].
#
# List the name(s) of your NZBGet categories (CategoryX.Name) that correspond to TV Shows (Comma Separated)
#tvCat=tv

# Custom Plex Section(s) you would like to Update [Optional].
#
# Section Number(s) Corresponding to your Plex Library (Comma Seperated). These sections will only refreshed if Library Refesh Mode is set to Custom or Both
#customPlexSection=

## Plex Home Theater

# Plex Home Theater Settings [Optional].
#
# Host IP(s) of your Plex Home Theater Client(s) (Comma Separated)
#clientsIP=192.168.1.XXX

# Use Silent Failure Mode (yes,no).
#
# Activate if you want NZBGet to report a SUCCESS status regardless of Errors, in cases where PMS is offline.
#silentFailure=no

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import StringIO
import requests
import json
import xml.etree.cElementTree as ET
from requests.auth import HTTPBasicAuth

POSTPROCESS_SUCCESS = 93
POSTPROCESS_ERROR = 94
POSTPROCESS_NONE = 95

if not 'NZBPP_STATUS' in os.environ:
    print('*** NZBGet post-processing script ***')
    print('This script is supposed to be called from NZBGet v13.0 or later.')
    sys.exit(POSTPROCESS_ERROR)

required_options = ('NZBPO_SILENTFAILURE', 'NZBPO_MOVIESCAT', 'NZBPO_TVCAT', 'NZBPO_REFRESHMODE',
                    'NZBPO_REFRESHLIBRARY', 'NZBPO_DHEADERS', 'NZBPO_GUISHOW', 'NZBPO_PLEXUSER', 'NZBPO_PLEXPASS')
for optname in required_options:
    if (not optname in os.environ):
        print('[ERROR] NOTIFYPLEX: Option %s is missing in configuration file. Please check script settings' % optname[6:])
        sys.exit(POSTPROCESS_ERROR)

#Check to see if download was successful
ppStatus = os.environ['NZBPP_STATUS'].startswith('SUCCESS/')

dnzboptions = ('NZBPR__DNZB_PROPERNAME', 'NZBPR__DNZB_EPISODENAME', 'NZBPR__DNZB_MOVIEYEAR')
if os.environ.has_key(dnzboptions[0]):
    properName = os.environ[dnzboptions[0]]
else:
    properName = ''
if os.environ.has_key(dnzboptions[1]):
    properEP = os.environ[dnzboptions[1]]
else:
    properEP = ''
if os.environ.has_key(dnzboptions[2]):
    properYear = os.environ[dnzboptions[2]]
else:
    properYear = ''

nzbName = os.environ['NZBPP_NZBNAME']
nzbCat = os.environ['NZBPP_CATEGORY']
guiShow = os.environ['NZBPO_GUISHOW'] == 'yes'
plexUsername = os.environ['NZBPO_PLEXUSER']
plexPassword = os.environ['NZBPO_PLEXPASS']
refreshLibrary = os.environ['NZBPO_REFRESHLIBRARY'] == 'yes'
refreshMode = os.environ['NZBPO_REFRESHMODE']
silentMode = os.environ['NZBPO_SILENTFAILURE'] == 'yes'


def getAuthToken(plexUser, plexPass):

    urlAuth = 'https://my.plexapp.com/users/sign_in.xml'
    headers = {
        'X-Plex-Platform': 'NZBGet',
        'X-Plex-Platform-Version': '14.0',
        'X-Plex-Provides': 'controller',
        'X-Plex-Product': 'NotifyPlex',
        'X-Plex-Version': "2.0",
        'X-Plex-Device': 'NZBGet',
        'X-Plex-Client-Identifier': '12286'
    }
    try:
        token = None
        auth = requests.post(urlAuth, headers=headers, auth=HTTPBasicAuth(plexUser, plexPass))
        strResponse = StringIO.StringIO(auth.content)
        tree = ET.parse(strResponse)
        for elem in tree.getiterator():
            if (elem.tag == 'authentication-token'):
                token = elem.text.strip()
                print('[INFO] NOTIFYPLEX: Plex.tv Authentication Successful')
                return token
    except requests.Timeout or requests.ConnectionError or requests.HTTPError:
        if silentMode:
            print('[WARNING] NOTIFYPLEX: There was an Error Authenticating. Silent Failure Mode Activated')
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            print('[ERROR] NOTIFYPLEX: Error Authenticating using Plex.tv')
            sys.exit(POSTPROCESS_ERROR)
    if (token == None):
        if silentMode:
            print('[WARNING] NOTIFYPLEX: There was an Error Authenticating. Silent Failure Mode Activated')
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            print('[ERROR] NOTIFYPLEX: Error Authenticating using Plex.tv')
            sys.exit(POSTPROCESS_ERROR)


def refreshAuto(movieCATs, tvCATs, plexIP):

    movieCATs = movieCATs.replace(' ', '')
    movieCATSplit = movieCATs.split(',')
    tvCATs = tvCATs.replace(' ', '')
    tvCATSplit = tvCATs.split(',')

    params = {
        'X-Plex-Token': getAuthToken(plexUsername, plexPassword)
    }

    url = 'http://%s/library/sections' % (plexIP)
    try:
        secXML = requests.get(url, params=params, verify=False, timeout=10)
    except requests.Timeout or requests.ConnectionError or requests.HTTPError:
        if silentMode:
            print('[WARNING] NOTIFYPLEX: Error Auto-Detecting Plex Sections. Silent Failure Mode Activated')
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            print('[ERROR] NOTIFYPLEX: Error Auto-Detecting Plex Sections. Check Network Connection and Plex Server IP, Port')
            sys.exit(POSTPROCESS_ERROR)

    strResponse = StringIO.StringIO(secXML.content)
    tree = ET.parse(strResponse)
    movieSections = []
    tvSections = []
    for elem in tree.getiterator('Directory'):
        if (elem.attrib['type'] == 'show'):
            tvSections.append(elem.attrib['key'])
        elif (elem.attrib['type'] == 'movie'):
            movieSections.append(elem.attrib['key'])

    for tCat in tvCATSplit:
        if (nzbCat == tCat):
            for tSection in tvSections:
                url = 'http://%s/library/sections/%s/refresh' % (plexIP, tSection)
                try:
                    r = requests.get(url, params=params, verify=False, timeout=10)
                except requests.Timeout or requests.ConnectionError or requests.HTTPError:
                    if silentMode:
                        print('[WARNING] NOTIFYPLEX: Error Updating Section %s. Silent Failure Mode Activated' % tSection)
                        sys.exit(POSTPROCESS_SUCCESS)
                    else:
                        print(
                            '[ERROR] NOTIFYPLEX: Error Opening URL. Check Network Connection and Plex Server IP, Port, and Section Numbers')
                        sys.exit(POSTPROCESS_ERROR)
                print('[INFO] NOTIFYPLEX: Targeted PLEX Update for Section %s Complete' % tSection)

    for mCat in movieCATSplit:
        if (nzbCat == mCat):
            for mSection in movieSections:
                url = 'http://%s/library/sections/%s/refresh' % (plexIP, mSection)
                try:
                    r = requests.get(url, params=params, verify=False, timeout=10)
                except requests.Timeout or requests.ConnectionError or requests.HTTPError:
                    if silentMode:
                        print('[WARNING] NOTIFYPLEX: Error Updating Section %s. Silent Failure Mode Activated' % mSection)
                        sys.exit(POSTPROCESS_SUCCESS)
                    else:
                        print(
                            '[ERROR] NOTIFYPLEX: Error Opening URL. Check Network Connection and Plex Server IP, Port, and Section Numbers')
                        sys.exit(POSTPROCESS_ERROR)
                print('[INFO] NOTIFYPLEX: Targeted PLEX Update for Section %s Complete' % mSection)


def refreshCustomSections(rawPlexSections, plexIP):

    plexSections = rawPlexSections.replace(' ', '')
    plexSectionsSplit = plexSections.split(',')

    params = {
        'X-Plex-Token': getAuthToken(plexUsername, plexPassword)
    }

    for plexSection in plexSectionsSplit:
        url = 'http://%s/library/sections/%s/refresh' % (plexIP, plexSection)
        try:
            r = requests.get(url, params=params, verify=False, timeout=10)
        except requests.Timeout or requests.ConnectionError or requests.HTTPError:
            if silentMode:
                print('[WARNING] NOTIFYPLEX: Error Updating Section %s. Silent Failure Mode Activated' % plexSection)
                sys.exit(POSTPROCESS_SUCCESS)
            else:
                print('[ERROR] NOTIFYPLEX: Error Opening URL. Check Network Connection and Plex Server IP, Port, and Section Numbers')
                sys.exit(POSTPROCESS_ERROR)
        print('[INFO] NOTIFYPLEX: Targeted PLEX Update for Section %s Complete' % plexSection)


def showGUINotifcation(rawPHTIPs):

    dHeaders = os.environ['NZBPO_DHEADERS'] == 'yes'
    phtURL = rawPHTIPs.replace(' ', '')
    phtURLSplit = phtURL.split(',')
    for phtURL in phtURLSplit:
        if dHeaders:
            if properName != '' and properEP != '':
                guiText = properName + ' - ' + properEP
            elif properName != '' and properYear != '':
                guiText = properName + ' (' + properYear + ')'
            elif properName == '' and properEP == '':
                guiText = nzbName
            else:
                guiText = properName
        else:
            guiText = nzbName

        phtRpcURL = 'http://%s:3005/jsonrpc' % phtURL
        headers = {'content-type': 'application/json'}
        payLoad = {'id': 1, 'jsonrpc': '2.0', 'method': 'GUI.ShowNotification',
                   'params': {'title': 'Downloaded', 'message': guiText}}
        try:
            d = requests.post(phtRpcURL, data=json.dumps(payLoad), headers=headers, timeout=10)
            print('[INFO] NOTIFYPLEX: GUI Notification to PHT Successful')
        except requests.exceptions.ConnectionError or requests.Timeout or requests.HTTPError:
            print('[WARNING] NOTIFYPLEX: Plex GUI Notification Failed')


if ppStatus:

    if guiShow:
        phtURLs = os.environ['NZBPO_CLIENTSIP']
        showGUINotifcation(phtURLs)

    if refreshLibrary:
        plexIP = os.environ['NZBPO_PLEXIP']
        rawPlexSection = os.environ['NZBPO_CUSTOMPLEXSECTION']
        mCats = os.environ['NZBPO_MOVIESCAT']
        tCats = os.environ['NZBPO_TVCAT']

        if (refreshMode == 'Custom'):
            refreshCustomSections(rawPlexSection, plexIP)
        elif (refreshMode == 'Auto'):
            refreshAuto(mCats, tCats, plexIP)
        else:
            refreshCustomSections(rawPlexSection, plexIP)
            refreshAuto(mCats, tCats, plexIP)

    sys.exit(POSTPROCESS_SUCCESS)

else:
    print('[WARNING] NOTIFYPLEX: Skipping Plex Update because download failed.')
    sys.exit(POSTPROCESS_NONE)
