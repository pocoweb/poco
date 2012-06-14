#!/usr/bin/env python

import sys
import pymongo
import random
import hashlib
import settings


# http://www.aspheute.com/english/20040105.asp
def createRandomPassword(length):
    allowedChars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ23456789"
    password = ""
    for i in range(length):
        password += allowedChars[random.randint(0, 256) % len(allowedChars)]
    return password

def createHashedPassword(password):
    salt = createRandomPassword(16)
    hashed_password = hashlib.sha256(password + salt).hexdigest()
    return hashed_password, salt


connection = pymongo.Connection(settings.mongodb_host)
admin_users = connection["tjb-db"]["admin-users"]

random.seed(open("/dev/random", "rb").read(10))


def cmd_createNewUser():
    while True:
        user_name = raw_input("name:")
        if admin_users.find_one({"user_name": user_name}) is None:
            break
        else:
            print "user already exists."
    

    password = createRandomPassword(10)
    print "password is:", password

    hashed_password, salt = createHashedPassword(password)

    admin_users.insert({"user_name": user_name, "hashed_password": hashed_password, "salt": salt})


def _enterExistedUser():
    while True:
        user_name = raw_input("name:")
        user_in_db = admin_users.find_one({"user_name": user_name})
        if user_in_db is not None:
            break
        else:
            print "user does not exist."
    return user_in_db


def cmd_generateNewPassword():
    user = _enterExistedUser()

    password = createRandomPassword(10)
    print "password is:", password

    hashed_password, salt = createHashedPassword(password)
    
    admin_users.update({"user_name": user["user_name"]}, \
            {"$set": {"hashed_password": hashed_password, "salt": salt}})


def cmd_showUserInfo():
    user = _enterExistedUser()
    print user

while True:
    print "1. create New User"
    print "2. generate New Password"
    print "3. show user info"
    cmd = raw_input("enter a number:").strip()
    if cmd == "1":
        cmd_createNewUser()
    elif cmd == "2":
        cmd_generateNewPassword()
    elif cmd == "3":
        cmd_showUserInfo()
