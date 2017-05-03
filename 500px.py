#!/usr/bin/env python

#################################################################################
# Original 500px-Bot script by Kenshii                                          #
# Modified by Atomneo                                                           #
#################################################################################
# 1. Check accepted list                                                        #
# 1.1. If user is older than 30 days remove him                                 #
# 2. Check ignored list                                                         #
# 2.1. If user is older than 30 days remove him                                 #
# 3. Check pending list                                                         #
# 3.1. If user is older than 7 dayd remove him                                  #
#                                                                               #
# 4. Foreach followed users                                                     #
# 4.1. If user is accepted or pending - ignore                                  #
# 4.2. Else                                                                     #
# 4.2.1. If user is following us - add to accepted                              #
# 4.2.2. If user not following us - unfollow and add to ignored                 #
#                                                                               #
# 5. Foreach users that follows us                                              #
# 5.1. If user is accepted - ignore                                             #
# 5.2. Else                                                                     #
# 5.2.1. If user is pending - remove from pending                               #
# 5.2.2. Add user to accepted                                                   #
#                                                                               #
# 6. Foreach upcoming photo (may be changed to other categories)                #
# 6.1. If user is not accepted, pending or ignored follow him, add to pending   #
# 6.2. Calculate percentage and randomly like photo                             #
#################################################################################

import requests
import time
import json
import os
from bs4 import BeautifulSoup
from random import randint

# region configuration

loginParams = {
    'authenticity_token': '',  # Don't change me
    'session[email]': '',  # Change me
    'session[password]': ''  # Change me
}

# If user not followed us in this time unfollow user and add to ignored
pending_clear_time = 60 * 60 * 24 * 7  # 7 days

# Remove user from ignored after this time
ignored_clear_time = 60 * 60 * 24 * 30  # 30 days

# Remove user from accepted and check him again (add user to pending)
accepted_clear_time = 60 * 60 * 24 * 30  # 30 days

num_follows_wanted = 101  # 101 is the daily limit for follows, and any more than this fails. Don't increase.

num_likes_wanted = 200
like_chance = 25  # percents
minimal_rating = 74  # didn't like photo with rating lower than minimal rating # remarks - photos in upcoming has rating around 75
show_colors = True
base_wait_time = 7  # seconds

# endregion

# region initialization

scriptDirectory = os.path.abspath(os.path.dirname(__file__))
logDate = time.strftime('%Y-%m-%d')

userSession = requests.Session()
userSession.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'
})

pendingFileName = 'pendingUsers.txt'
acceptedFileName = 'acceptedUsers.txt'
ignoredFileName = 'ignoredUsers.txt'

pendingFilePath = scriptDirectory + '/' + pendingFileName
acceptedFilePath = scriptDirectory + '/' + acceptedFileName
ignoredFilePath = scriptDirectory + '/' + ignoredFileName

logFileName = logDate + '_log.txt'
logFilePath = scriptDirectory + '/logs/'

csrfHeaders = {
    'X-CSRF-Token': '',
    'X-Requested-With': 'XMLHttpRequest'
}

pending_follow_list = []
acceptedFollowList = []
ignoredFollowList = []

if show_colors:
    blue = '\033[94m'
    black = '\033[98m'
    grey = '\033[97m'
    green = '\033[92m'
    red = '\033[91m'
    yellow = '\033[93m'
    bold = '\033[1m'
    end_color = '\033[0m'
else:
    blue = ''
    black = ''
    grey = ''
    green = ''
    red = ''
    yellow = ''
    bold = ''
    end_color = ''

# endregion

# region files functions


def printToLog(string):
    global logFilePath, logFileName
    log_time = time.strftime('%H:%M:%S')
    if not os.path.exists(logFilePath):
        os.makedirs(logFilePath)
    with open(logFilePath + logFileName, 'a+') as f:
        f.write(log_time + ' - ' + string + '\n')
    print(grey + log_time + ' - ' + end_color + string)


def loadListsFromFiles():
    global pendingFilePath, acceptedFilePath, ignoredFilePath
    global pending_follow_list, acceptedFollowList, ignoredFollowList
    if os.path.exists(pendingFilePath):
        with open(pendingFilePath, 'r') as f:
            pending_follow_list = json.loads(f.read())
    if os.path.exists(acceptedFilePath):
        with open(acceptedFilePath, 'r') as f:
            acceptedFollowList = json.loads(f.read())
    if os.path.exists(ignoredFilePath):
        with open(ignoredFilePath, 'r') as f:
            ignoredFollowList = json.loads(f.read())


def saveIgnored():
    with open(ignoredFilePath, 'w') as f:
        f.write(json.dumps(ignoredFollowList))


def savePending():
    with open(pendingFilePath, 'w') as f:
        f.write(json.dumps(pending_follow_list))


def saveAccepted():
    with open(acceptedFilePath, 'w') as f:
        f.write(json.dumps(acceptedFollowList))

# endregion

# region offline functions


def isUserPending(target_user_name):
    global pending_follow_list
    for i, v in enumerate(pending_follow_list):
        if v['name'] == target_user_name:
            return True
    return False


def isUserAccepted(target_user_name):
    global acceptedFollowList
    for i, v in enumerate(acceptedFollowList):
        if v['name'] == target_user_name:
            return True
    return False


def isUserIgnored(target_user_name):
    global ignoredFollowList
    for i, v in enumerate(ignoredFollowList):
        if v['name'] == target_user_name:
            return True
    return False


def addUserToPendingList(target_user_name):
    global pending_follow_list, pendingFilePath
    if target_user_name in pending_follow_list:
        return
    pending_follow_list.append({'name': target_user_name, 'time_followed': time.time()})
    printToLog(blue + 'Adding user ' + target_user_name + ' to pending.' + end_color)
    savePending()


def addUserToAcceptedList(target_user_name):
    global acceptedFollowList, acceptedFilePath
    if target_user_name in acceptedFollowList:
        return
    acceptedFollowList.append({'name': target_user_name, 'time_followed': time.time()})
    printToLog(green + 'Adding user ' + target_user_name + ' to accepted.' + end_color)
    saveAccepted()


def addUserToIgnoredList(target_user_name):
    global ignoredFollowList, ignoredFilePath
    if target_user_name in ignoredFollowList:
        return
    ignoredFollowList.append({'name': target_user_name, 'time_followed': time.time()})
    printToLog(yellow + 'Adding user ' + target_user_name + ' to ignored.' + end_color)
    saveIgnored()


def removeUserFromPendingList(target_user_name):
    global pending_follow_list, pendingFilePath
    for i, v in enumerate(list(pending_follow_list)):
        if v['name'] == target_user_name:
            pending_follow_list.remove(v)
            break
    savePending()


def removeUserFromAcceptedList(target_user_name):
    global acceptedFollowList, acceptedFilePath
    for i, v in enumerate(list(acceptedFollowList)):
        if v['name'] == target_user_name:
            acceptedFollowList.remove(v)
            break
    saveAccepted()


def removeUserFromIgnoredList(target_user_name):
    global ignoredFollowList, ignoredFilePath
    for i, v in enumerate(list(ignoredFollowList)):
        if v['name'] == target_user_name:
            ignoredFollowList.remove(v)
            break
    saveIgnored()


def checkAccepted():
    global i, v
    for i, v in enumerate(list(acceptedFollowList)):
        if current_time - v['time_followed'] < accepted_clear_time:
            continue
        removeUserFromAcceptedList(v['name'])
        # addUserToPendingList(v['name'])


def checkIgnored():
    global i, v
    for i, v in enumerate(list(ignoredFollowList)):
        if current_time - v['time_followed'] < ignored_clear_time:
            continue
        removeUserFromIgnoredList(v['name'])


def checkPending():
    global i, v
    for i, v in enumerate(list(pending_follow_list)):
        if current_time - v['time_followed'] < pending_clear_time:
            continue
        removeUserFromPendingList(v['name'])
        # addUserToIgnoredList(v['name'])


def wait(rand):
    time.sleep(base_wait_time + randint(0, rand))

# endregion

# region online functions


def followUser(target_user_name):
    global userSession, num_follows_done, csrfHeaders
    continue_loop = True
    while continue_loop:
        try:
            follow_resp = userSession.post('https://500px.com/' + target_user_name + '/follow', timeout=5, headers=csrfHeaders)
            if follow_resp.status_code == 200:
                num_follows_done += 1
                printToLog('Followed ' + target_user_name + ' (' + str(num_follows_done) + ' of ' + str(num_follows_wanted) + ').')
                addUserToPendingList(target_user_name)
                continue_loop = False
            elif follow_resp.status_code == 404:
                printToLog('User ' + target_user_name + ' no longer exists. Skipped follow.')
                continue_loop = False
            elif follow_resp.status_code == 403:
                printToLog('Already followed ' + target_user_name + '.')
                continue_loop = False
            else:
                printToLog('A server error (' + str(follow_resp.status_code) + ') occured. Retrying...')
                printToLog('Error page: ' + follow_resp.url)
                wait(0)
        except requests.exceptions.RequestException:
            printToLog('Web page timed out. Retrying...')
            wait(0)
    wait(5)


def unfollowUser(target_user_name):
    global userSession, csrfHeaders
    continue_loop = True
    while continue_loop:
        try:
            unfollow_resp = userSession.post('https://500px.com/' + target_user_name + '/unfollow', timeout = 5, headers = csrfHeaders)
            if unfollow_resp.status_code == 200:
                printToLog(red + 'Unfollowed ' + target_user_name + '.' + end_color)
                continue_loop = False
            elif unfollow_resp.status_code == 404:
                printToLog('User ' + target_user_name + ' no longer exists. Skipped unfollow.')
                continue_loop = False
            else:
                printToLog('A server error (' + str(unfollow_resp.status_code) + ') occured. Retrying...')
                printToLog('Error page: ' + unfollow_resp.url)
                time.sleep(5)
        except requests.exceptions.RequestException:
            printToLog('Web page timed out. Retrying...')
            wait(0)
    wait(5)


def getFollowing():
    global my_user_info, csrfHeaders
    page_num = 1
    following = []
    while True:
        following_page = requestWebPage('GET', 'https://api.500px.com/v1/users/' + str(my_user_info['id']) + '/friends?fullformat=0&page=' + str(page_num) + '&rpp=50', headers = csrfHeaders)
        following_page_json = json.loads(following_page.text)
        following += following_page_json['friends']
        if page_num == following_page_json['friends_pages']:
            break
        page_num += 1
        wait(10)
    return following


def getFollowers():
    global my_user_info
    page_num = 1
    followers = []
    while True:
        followers_page = requestWebPage('GET', 'https://api.500px.com/v1/users/' + str(my_user_info['id']) + '/followers?fullformat=0&page=' + str(page_num) + '&rpp=50')
        followers_page_json = json.loads(followers_page.text)
        followers += followers_page_json['followers']
        if page_num == followers_page_json['followers_pages']:
            break
        page_num += 1
        wait(10)
    return followers


def requestWebPage(method, url, data={}, headers={}, check_status_code=True):
    global userSession
    while True:
        try:
            response = userSession.request(method, url, data=data, headers=headers, timeout=5)
        except requests.exceptions.RequestException:
            printToLog('Web page timed out. Retrying...')
            wait(0)
            continue
        if check_status_code and response.status_code != 200:
            printToLog('A server error (' + str(response.status_code) + ') occured. Retrying...')
            printToLog('Error page: ' + response.url)
            wait(0)
            continue
        return response


def login():
    global my_user_info
    # This is used in order to obtain the authenticity token required for logging in.
    login_page = requestWebPage('GET', 'https://500px.com/login')
    printToLog('Retrieved login page.')
    wait(3)
    login_page_soup = BeautifulSoup(login_page.text, 'html.parser')
    loginParams['authenticity_token'] = login_page_soup.find('meta', {'name': 'csrf-token'}).get('content')
    csrfHeaders['X-CSRF-Token'] = loginParams['authenticity_token']
    # This is the actual login request.
    user_login = requestWebPage('POST', 'https://api.500px.com/v1/session', data=loginParams)
    printToLog('Logged in successfully.')
    wait(10)
    # Getting my user info from login response.
    my_user_info = json.loads(user_login.text)['user']


def reviewFollowedAndFollowers():
    followers = getFollowers()
    printToLog('Obtained a list of followers. (' + str(len(followers)) + ')')
    following = getFollowing()
    printToLog('Obtained a list of people we\'re following (' + str(len(following)) + ').')
    for following_user in following:
        if isUserAccepted(following_user['username']) or isUserPending(following_user['username']):
            printToLog(grey + 'User ' + following_user['username'] + ' is accepted or pending - ignoring.' + end_color)
            continue

        # if following user follows us
        if any(follower['username'] == following_user['username'] for follower in followers):
            addUserToAcceptedList(following_user['username'])
            continue

        unfollowUser(following_user['username'])
        addUserToIgnoredList(following_user['username'])
        printToLog(red + following_user['username'] + ' isn\'t following you and isn\'t pending. Ignored and unfollowed.' + end_color)
    printToLog('Finished comparing followers against following.')
    for follower in list(followers):
        # current_time = time.time()
        if not isUserPending(follower['username']):
            followers.remove(follower)
            continue
        removeUserFromPendingList(follower['username'])
        addUserToAcceptedList(follower['username'])
        printToLog(green + follower['username'] + ' followed you. Accepted.' + end_color)
        # pending_user_names.remove(follower['username'])
        followers.remove(follower)

        # for follower in list(pending_follow_list):
        # current_time = time.time()
        # if current_time - follower['time_followed'] <= 172800:
        #    continue
        # removeUserFromPendingList(follower['name'])
        # unfollowUser(follower['name'])
        # addUserToIgnoredList(follower['name'])
        # pending_user_names.remove(follower['name'])
        # printToLog(follower['name'] + ' didn\'t follow you. Ignored and unfollowed.')
    printToLog('Review of followed users finished.')


def followNewPeople():
    global page_num
    while num_follows_done < num_follows_wanted:
        upcoming_page = requestWebPage('GET', 'https://api.500px.com/v1/photos?feature=upcoming&include_states=false&page=' + str(page_num) + '&rpp=50', headers=csrfHeaders)
        upcoming_page_json = json.loads(upcoming_page.text)
        for upcoming_photo in upcoming_page_json['photos']:
            user_name = upcoming_photo['user']['username']
            if num_follows_done == num_follows_wanted:
                break
            if not isUserPending(user_name) and not isUserAccepted(user_name) and not isUserIgnored(user_name):
                followUser(user_name)
            else:
                printToLog(grey + 'Skipping ' + user_name + '.' + end_color)
        page_num += 1
        wait(10)
    printToLog('Finished. No more users left to follow.')


def likeSomePhotos():
    global page_num, num_likes_done
    page_num = 1
    while num_likes_done < num_likes_wanted:
        upcoming_page = requestWebPage('GET', 'https://api.500px.com/v1/photos?feature=upcoming&include_states=false&page=' + str(page_num) + '&rpp=50', headers=csrfHeaders)
        upcoming_page_json = json.loads(upcoming_page.text)
        for upcoming_photo in upcoming_page_json['photos']:
            photo_rating = upcoming_photo['rating']
            photo_id = upcoming_photo['id']

            if num_likes_done == num_likes_wanted:
                break

            if photo_rating < minimal_rating:
                continue

            if randint(0, 100) > like_chance:
                continue

            likePhoto(photo_id)
        page_num += 1
        wait(10)
    printToLog('Finished. No more photos left to like.')


def likePhoto(photo_id):
    global userSession, num_likes_done, csrfHeaders
    continue_loop = True
    while continue_loop:
        try:
            like_resp = userSession.post('https://api.500px.com/v1/photos/' + str(photo_id) + '/vote?vote=1', timeout=5, headers=csrfHeaders)
            if like_resp.status_code == 200:
                num_likes_done += 1
                printToLog('Liked ' + str(photo_id) + ' (' + str(num_likes_done) + ' of ' + str(num_likes_wanted) + ').')
                continue_loop = False
            elif like_resp.status_code == 404:
                printToLog('Photo ' + str(photo_id) + ' no longer exists. Skipped like.')
                continue_loop = False
            elif like_resp.status_code == 403:
                printToLog('Already liked ' + str(photo_id) + '.')
                continue_loop = False
            else:
                printToLog('A server error (' + str(like_resp.status_code) + ') occured. Retrying...')
                printToLog('Error page: ' + like_resp.url)
                time.sleep(5)
        except requests.exceptions.RequestException:
            printToLog('Web page timed out. Retrying...')
            wait(0)
    wait(5)


def followNewPeopleAndLikeSomePhotos():
    global page_num
    while num_follows_done < num_follows_wanted:
        upcoming_page = requestWebPage('GET', 'https://api.500px.com/v1/photos?feature=upcoming&include_states=false&page=' + str(page_num) + '&rpp=50', headers=csrfHeaders)
        upcoming_page_json = json.loads(upcoming_page.text)
        for upcoming_photo in upcoming_page_json['photos']:
            user_name = upcoming_photo['user']['username']
            photo_rating = upcoming_photo['rating']
            photo_id = upcoming_photo['id']

            if photo_rating >= minimal_rating and num_likes_done < num_likes_wanted and randint(0, 100) > like_chance:
                likePhoto(photo_id)

            if num_follows_done == num_follows_wanted:
                break

            if not isUserPending(user_name) and not isUserAccepted(user_name) and not isUserIgnored(user_name):
                followUser(user_name)
            else:
                printToLog(grey + 'Skipping ' + user_name + '.' + end_color)
        page_num += 1
        wait(10)
    printToLog('Finished. No more users left to follow.')

# endregion

# region main


def main():
    global current_time, page_num

    # Retrieving the list of currently pending followed users by the bot (and other lists).
    loadListsFromFiles()

    # Checking and clearing lists, moving users between lists
    # 1., 2., 3.
    checkPending()
    checkAccepted()
    checkIgnored()

    login()

    # Time to see who has actually bothered following us.
    # pending_user_names = [pending_follow_user['name'] for pending_follow_user in pending_follow_list]

    reviewFollowedAndFollowers()

    # Time to view the up-and-coming and follow more people :)
    # followNewPeople()

    # Like random photos
    # likeSomePhotos()

    followNewPeopleAndLikeSomePhotos()

my_user_info = None
page_num = 1  # Do not change.
num_follows_done = 0  # Do not change.
num_likes_done = 0
current_time = time.time()
main()

# endregion
