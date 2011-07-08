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
users = connection["tjb-db"]["users"]

random.seed(open("/dev/random", "rb").read(10))


def _inputSites():
    sites_str = raw_input("sites(comma separated):").strip()
    if sites_str == "":
        return []
    else:
        return sites_str.split(",")


def cmd_createNewUser():
    while True:
        user_name = raw_input("name:")
        if users.find_one({"user_name": user_name}) is None:
            break
        else:
            print "user already exists."
    
    sites = _inputSites()

    password = createRandomPassword(10)
    print "password is:", password

    hashed_password, salt = createHashedPassword(password)

    users.insert({"user_name": user_name, "hashed_password": hashed_password, "salt": salt,
                  "sites": sites})


def _enterExistedUser():
    while True:
        user_name = raw_input("name:")
        user_in_db = users.find_one({"user_name": user_name})
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
    
    users.update({"user_name": user["user_name"]}, \
            {"$set": {"hashed_password": hashed_password, "salt": salt}})

def cmd_updateSite():
    user = _enterExistedUser()
    sites = _inputSites()
    users.update({"user_name": user["user_name"]}, {"$set": {"sites": sites}})

def cmd_addSite():
    user = _enterExistedUser()
    sites = user["sites"]
    sites = sites + _inputSites()
    sites = list(set(sites))
    sites.sort()
    users.update({"user_name": user["user_name"]}, {"$set": {"sites": sites}})

def cmd_showUserInfo():
    user = _enterExistedUser()
    print user

while True:
    print "1. create New User"
    print "2. generate New Password"
    print "3. update managed sites"
    print "4. add managed sites"
    print "5. show user info"
    cmd = raw_input("enter a number:").strip()
    if cmd == "1":
        cmd_createNewUser()
    elif cmd == "2":
        cmd_generateNewPassword()
    elif cmd == "3":
        cmd_updateSite()
    elif cmd == "4":
        cmd_addSite()   
    elif cmd == "5":
        cmd_showUserInfo()
