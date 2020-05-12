#!/usr/bin/env python
#
##############################################################################
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Post-Processing Script to Update Plex Library and Notify PHT.
#
# This script triggers a targeted library update to your Plex Media Server and sends a GUI Notification to Plex Home Theater.
# Auto-Detection of NZBGet category and Plex sections is now supported. This script also works with Plex Home enabled.
#
# Copyright (C) 2019 mannibis
# Version 2.1.3
#
#
# NOTE: This script is compatible to Python 2.x and Python 3.x, check README file for installation instructions.

##############################################################################
### OPTIONS                                                                ###

## General

# Use Silent Failure Mode (yes,no).
#
# Activate if you want NZBGet to report a SUCCESS status regardless of errors, in cases where PMS is offline.
#silentFailure=no

## Plex Media Server

# Refresh Plex Library (yes,no).
#
# Activate if you want NotifyPlex to refresh your Plex library
#refreshLibrary=no

# Plex.tv Username [Required to generate Plex Auth-Token]
#PlexUser=

# Plex.tv Password [Required to generate Plex Auth-Token]
#PlexPassword=

# Authorize script with Plex server [Required if refreshLibrary is enabled].
#
# Once authorized, it will be visible in your Plex server settings as "NotifyPlex"
# in the "Authorized Devices" section.
#PlexAuthorize@Generate Plex Auth-Token

# Auth-Token for this script.
#
# Use the above button to authorize this script with Plex.tv
# NOTE: The Password can be safely removing when setting the Auth-Token.
#PlexAuthToken=

# Plex Media Server Host.
#
# IP or hostname of your Plex Media Server including port (only 1 server is supported)
#PlexHost=192.168.1.XXX:32400

# Library Refresh Mode (Auto,Custom,Both).
#
# Select Refresh Mode: Auto will automatically detect your NZBGet category and refresh the appropriate sections, Custom will only refresh the sections you input into the Custom sections setting below, Both will auto-detect and refresh the Custom Sections
#refreshMode=Auto

# NZBGet Movies Category/Categories [Required for Auto Mode].
#
# List the name(s) of your NZBGet categories (CategoryX.Name) that correspond to Movies (comma separated)
#moviesCat=movies

# NZBGet TV Category/Categories [Required for Auto Mode].
#
# List the name(s) of your NZBGet categories (CategoryX.Name) that correspond to TV Shows (comma separated)
#tvCat=tv

# Custom Plex Section(s) you would like to update [Optional].
#
# Section Number(s) corresponding to your Plex library (comma separated). These sections will only refreshed if Library Refesh Mode is set to Custom or Both
#customPlexSection=

## Plex Home Theater

# Send GUI Notification to Plex Home Theater (yes,no).
#
# Activate if you want NotifyPlex to Send a GUI notification to Plex Home Theater
#guiShow=no

# Use Direct NZB ProperName for notification (yes,no).
#
# Activate if you want to use the DNZB Header ProperName for the title of the media if available
#dHeaders=yes

# Plex Home Theater Settings [Optional].
#
# Host IP(s) of your Plex Home Theater client(s) (comma separated)
#clientsIP=192.168.1.XXX

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################

import os
import sys
import json
from xml.etree.ElementTree import fromstring

POSTPROCESS_SUCCESS = 93
POSTPROCESS_ERROR = 94
POSTPROCESS_NONE = 95

try:
    import requests
except ImportError:
    print('[ERROR] NOTIFYPLEX: Missing python package "requests". Please follow installation instructions in the '
          'README file')
    sys.exit(POSTPROCESS_ERROR)


def get_auth_token(username, password):
    auth_url = 'https://my.plexapp.com/users/sign_in.xml'
    auth_params = {'user[login]': username, 'user[password]': password}
    headers = {
        'X-Plex-Platform': 'NZBGet',
        'X-Plex-Platform-Version': '21.0',
        'X-Plex-Provides': 'controller',
        'X-Plex-Product': 'NotifyPlex',
        'X-Plex-Version': "2.1.3",
        'X-Plex-Device': 'NZBGet',
        'X-Plex-Client-Identifier': '12287'
    }

    try:
        auth_response = requests.post(auth_url, headers=headers, data=auth_params)
        auth_response.raise_for_status()
    except requests.RequestException:
        return None
    else:
        root = fromstring(auth_response.content)
        return root.attrib['authToken']


def refresh_auto(movie_cats, tv_cats):
    print('[DETAIL] NOTIFYPLEX: Auto-refreshing Plex Library')
    movie_cats = movie_cats.replace(' ', '')
    movie_cats_split = movie_cats.split(',')
    tv_cats = tv_cats.replace(' ', '')
    tv_cats_split = tv_cats.split(',')

    try:
        url = 'http://%s/library/sections' % plex_host
        params = {'X-Plex-Token': plex_auth_token}
        section_response = requests.get(url, params=params, timeout=10)
        section_response.raise_for_status()
    except requests.RequestException as e:
        if silent_mode:
            print('[WARNING] NOTIFYPLEX: Failed auto-detecting Plex sections. Silent failure mode active')
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            print('[ERROR] NOTIFYPLEX: Failed auto-detecting Plex sections. Check Network Connection, Plex server '
                  'settings, Auth-Token and section numbers.')
            print('[ERROR] NOTIFYPLEX: %s' % e)
            sys.exit(POSTPROCESS_ERROR)

    root = fromstring(section_response.content)
    plex_sections = {'movie': [], 'show': []}

    for directory in root.findall('Directory'):
        directory_type = directory.get('type')
        section_id = directory.get('key')
        if directory_type in plex_sections.keys():
            plex_sections[directory_type].append(section_id)

    if nzb_cat in tv_cats_split:
        refresh_sections(plex_sections['show'], plex_auth_token)
    elif nzb_cat in movie_cats_split:
        refresh_sections(plex_sections['movie'], plex_auth_token)
    else:
        if silent_mode:
            print('[WARNING] NOTIFYPLEX: Category "%s" is not configured as a section to be refreshed. '
                  'Silent failure mode active' % nzb_cat)
            sys.exit(POSTPROCESS_SUCCESS)
        else:
            print('[ERROR] NOTIFYPLEX: Category "%s" is not configured as a section to be refreshed.' % nzb_cat)
            sys.exit(POSTPROCESS_ERROR)


def refresh_custom_sections(raw_custom_section_ids):
    print('[DETAIL] NOTIFYPLEX: Refreshing custom sections')
    custom_section_ids = raw_custom_section_ids.replace(' ', '')
    custom_section_ids = custom_section_ids.split(',')
    refresh_sections(custom_section_ids, plex_auth_token)


def refresh_sections(plex_sections, auth_token):
    params = {'X-Plex-Token': auth_token}

    for section_id in plex_sections:
        refresh_url = 'http://%s/library/sections/%s/refresh' % (plex_host, section_id)
        try:
            response = requests.get(refresh_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            if silent_mode:
                print('[WARNING] NOTIFYPLEX: Failed updating section %s. Silent failure mode active' % section_id)
                sys.exit(POSTPROCESS_SUCCESS)
            else:
                print('[ERROR] NOTIFYPLEX: Failed updating section %s. Check Network Connection, Plex server '
                      'settings, Auth-Token and section numbers.' % section_id)
                print('[ERROR] NOTIFYPLEX: %s' % e)
                sys.exit(POSTPROCESS_ERROR)
        else:
            print('[INFO] NOTIFYPLEX: Targeted Plex update for section %s complete' % section_id)


def show_gui_notification(raw_pht_ips):
    print('[DETAIL] NOTIFYPLEX: Sending GUI notification')
    d_headers = os.environ['NZBPO_DHEADERS'] == 'yes'
    pht_url = raw_pht_ips.replace(' ', '')
    pht_url_split = pht_url.split(',')
    for pht_url in pht_url_split:
        if d_headers:
            if (proper_name != '') and (proper_ep != ''):
                gui_text = '%s - %s' % (proper_name, proper_ep)
            elif (proper_name != '') and (proper_year != ''):
                gui_text = '%s (%s)' % (proper_name, proper_year)
            elif (proper_name == '') and (proper_ep == ''):
                gui_text = nzb_name
            else:
                gui_text = proper_name
        else:
            gui_text = nzb_name

        pht_rpc_url = 'http://%s:3005/jsonrpc' % pht_url
        headers = {'content-type': 'application/json'}
        payload = {
            'id': 1,
            'jsonrpc': '2.0',
            'method': 'GUI.ShowNotification',
            'params': {'title': 'Downloaded', 'message': gui_text}
        }
        try:
            requests.post(pht_rpc_url, data=json.dumps(payload), headers=headers, timeout=10)
        except requests.RequestException as e:
            print('[WARNING] NOTIFYPLEX: GUI Notification to PHT failed: %s' % e)
        else:
            print('[INFO] NOTIFYPLEX: GUI Notification to PHT successful')


NZBGetVersion = os.environ['NZBOP_VERSION']
if NZBGetVersion[0:5] < '11.1':
    print('[ERROR] This script requires NZBGet 11.1 or newer. Please update NZBGet')
    sys.exit(POSTPROCESS_ERROR)

required_options = ('NZBPO_SILENTFAILURE', 'NZBPO_REFRESHLIBRARY', 'NZBPO_DHEADERS', 'NZBPO_GUISHOW')
for optname in required_options:
    if optname not in os.environ:
        print('[ERROR] NOTIFYPLEX: Option %s is missing in configuration file. '
              'Please check script settings' % optname[6:])
        sys.exit(POSTPROCESS_ERROR)

dnzboptions = ('NZBPR__DNZB_PROPERNAME', 'NZBPR__DNZB_EPISODENAME', 'NZBPR__DNZB_MOVIEYEAR')
if dnzboptions[0] in os.environ:
    proper_name = os.environ[dnzboptions[0]]
else:
    proper_name = ''
if dnzboptions[1] in os.environ:
    proper_ep = os.environ[dnzboptions[1]]
else:
    proper_ep = ''
if dnzboptions[2] in os.environ:
    proper_year = os.environ[dnzboptions[2]]
else:
    proper_year = ''

gui_show = os.environ['NZBPO_GUISHOW'] == 'yes'
refresh_library = os.environ['NZBPO_REFRESHLIBRARY'] == 'yes'
silent_mode = os.environ['NZBPO_SILENTFAILURE'] == 'yes'

# Check if the script is executed from settings page with a custom command
command = os.environ.get('NZBCP_COMMAND')
authorize_mode = command == 'PlexAuthorize'
if command is not None and not authorize_mode:
    print('[ERROR] NOTIFYPLEX: Invalid command ' + command)
    sys.exit(POSTPROCESS_ERROR)

if authorize_mode:
    required_options = ('NZBPO_PLEXUSER', 'NZBPO_PLEXPASSWORD')
    for optname in required_options:
        if optname not in os.environ:
            print('[ERROR] NOTIFYPLEX: Option %s is missing in configuration file. '
                  'Please check script settings' % optname[6:])
            sys.exit(POSTPROCESS_ERROR)

    plex_username = os.environ['NZBPO_PLEXUSER']
    plex_password = os.environ['NZBPO_PLEXPASSWORD']
    plex_auth_token = get_auth_token(plex_username, plex_password)

    if plex_auth_token is not None:
        print('[DETAIL] Authorization to Plex.tv successful.')
        print('[INFO] Copy & paste into PlexAuthToken, then save and reload.')
        print('[INFO] Auth-Token: %s' % plex_auth_token)
        sys.exit(POSTPROCESS_SUCCESS)
    else:
        print('[ERROR] Authorization to Plex.tv failed. Please check your Username and Password.')
        sys.exit(POSTPROCESS_ERROR)

required_options = ('NZBPO_MOVIESCAT', 'NZBPO_PLEXAUTHTOKEN', 'NZBPO_PLEXHOST', 'NZBPO_REFRESHMODE', 'NZBPO_TVCAT')
for optname in required_options:
    if os.environ.get(optname) in (None, ''):
        print('[ERROR] NOTIFYPLEX: Option "%s" is missing or empty in configuration file. '
              'Please check script settings' % optname[6:])
        sys.exit(POSTPROCESS_ERROR)

raw_custom_section_ids = os.environ['NZBPO_CUSTOMPLEXSECTION']
movie_cats = os.environ['NZBPO_MOVIESCAT']
plex_auth_token = os.environ['NZBPO_PLEXAUTHTOKEN']
plex_host = os.environ['NZBPO_PLEXHOST']
refresh_mode = os.environ['NZBPO_REFRESHMODE']
tv_cats = os.environ['NZBPO_TVCAT']

# Get variables provided by NZBGet
nzb_cat = os.environ['NZBPP_CATEGORY']
nzb_name = os.environ['NZBPP_NZBNAME']
nzb_status = os.environ['NZBPP_STATUS']

# Check to see if download was successful
if nzb_status.startswith('SUCCESS/'):
    if gui_show:
        pht_urls = os.environ['NZBPO_CLIENTSIP']
        show_gui_notification(pht_urls)

    if refresh_library:
        if refresh_mode == 'Custom':
            refresh_custom_sections(raw_custom_section_ids)
        elif refresh_mode == 'Auto':
            refresh_auto(movie_cats, tv_cats)
        else:
            refresh_custom_sections(raw_custom_section_ids)
            refresh_auto(movie_cats, tv_cats)

    sys.exit(POSTPROCESS_SUCCESS)
else:
    print('[WARNING] NOTIFYPLEX: Skipping Plex update because download failed')
    sys.exit(POSTPROCESS_NONE)
