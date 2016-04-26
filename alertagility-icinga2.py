#!/usr/bin/python
import os
import sys
import glob
import linecache
import time
import json
import argparse
import requests
import logging.handlers
from socket import gethostname

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address='/dev/log')
formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
handler.setFormatter(formatter)
log.addHandler(handler)

API_URL = "https://<SUBDOMAIN>.alertagility.com/api/new_event"
QUEUE_FOLDER = "/tmp/alertagility_queue/"
LOCK_FILE = QUEUE_FOLDER+"alertagility.lock"
PID_FILE = QUEUE_FOLDER+"alertagility.pid"
DEBUG = False


def is_pid_running(pid):
    script=linecache.getline(os.path.join('/proc', str(pid), 'cmdline'), 1).split('\0')[0:2]
    for pid in filter(lambda x: x.isdigit() and x != str(pid), os.listdir('/proc')):
        other=linecache.getline(os.path.join('/proc', str(pid), 'cmdline'), 1).split('\0')[0:2]
        if script[0] == other[0] and os.path.basename(script[-1]) == os.path.basename(other[-1]):
            return True
        else:
            return False


def acquire_lock():
    current_pid = str(os.getpid())
    if os.path.isfile(PID_FILE):
        print "%s already exists" % PID_FILE
        # reading PID from file and convert it to int
        old_pid = int((open(PID_FILE).read()))
        if is_pid_running(current_pid):
            print "old process with PID:%s is still running, existing." % str(old_pid)
            sys.exit(1)
        else:
            print "old process with PID:%s is NOT running, creating new PID_FILE." % str(old_pid)
            open(PID_FILE, 'w').write(current_pid)
    else:
        # File doesn't exist, create the PID_FILE and return tru
        open(PID_FILE, 'w').write(current_pid)


def release_lock():
    if DEBUG: print '-D- Cleaning PID file.'
    try:
        os.remove(PID_FILE)
    except OSError:
        pass
    return


def generate_file_name():
    epoch_time = str(time.time())
    pid = str(os.getpid())
    return QUEUE_FOLDER+"msg_"+pid+"_"+epoch_time+".ag"


def check_queue_folder():
    try:
        os.stat(QUEUE_FOLDER)
    except:
        os.mkdir(QUEUE_FOLDER)


def collect_msg_data():
    data = {}
    for key in os.environ:
        data[key] = os.environ[key]
    data['generated_by'] = gethostname()
    data['alert_type'] = args.alert_type
    return data


# queues the messages and then calls for purge as well.
def queue_message():
    if DEBUG: print "Enqueuing the messages"
    payload = collect_msg_data()
    print payload
    msg_file = generate_file_name()
    with open(msg_file, 'w') as outfile:
        json.dump(payload, outfile)
        log.info("generated new alertagility msg:%s", msg_file)
    purge_messages()


def post_msg(payload):
    if 'ICINGA_SERVICE_AUTH_KEY' not in payload:
        print "Invalid message, skipping"
        return True
    alert_service_auth_key = payload['ICINGA_SERVICE_AUTH_KEY']
    headers = {'X-Auth-Key': alert_service_auth_key}
    r = requests.post(API_URL, headers=headers, data=json.dumps(payload))
    print("request.headers:%s" % r.request.headers)
    if r.status_code == 200:
        print "status:%s  response:%s" % (r.status_code, r.text)
        return r.status_code
    else:
        log.error("Failed to push status:%s response:%s" % (r.status_code, r.text))
        print "status:%s  response:%s" % (r.status_code, r.text)
        return r.status_code


def process_file(msg_file):
    if DEBUG: print "Processing %s" % msg_file
    with open(msg_file) as data_file:    
        payload = json.load(data_file)
        return post_msg(payload)


def purge_messages():
    if DEBUG: print "purging the messages"
    os.chdir(QUEUE_FOLDER)
    for msg_file in glob.glob("msg_*.ag"):
        status_code = process_file(msg_file)
        if status_code == 200:
            log.info("pushed new alertagility msg:%s", msg_file)
            remove_msg_file(msg_file)
        elif status_code == 400:
            log.info("corrupt msg file detected msg:%s", msg_file)
            os.rename(msg_file, msg_file+".rejected")
        else:
            log.info("failed to push msg:%s", msg_file)


def remove_msg_file(msg_file):
    if DEBUG: print '-D- Removing the processed msg file.'
    try:
        os.chdir(QUEUE_FOLDER)
        os.remove(msg_file)
    except OSError:
        pass
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AlertAgility Icinga2 Plugin')
    parser.add_argument('-a', action="store", dest="action", default="queue")
    parser.add_argument('-t', action="store", dest="alert_type")
    parser.add_argument('-d', action="store_true", dest="debug", default=False)    
    args = parser.parse_args()
    DEBUG = args.debug
    if DEBUG: print "Arguments passed:", args
    
    # call main
    acquire_lock()
    check_queue_folder()
    
    if args.action == "queue":
        queue_message()
    elif args.action == 'purge':
        purge_messages()
    else:
        print "Action should be one of 'queue' or 'purge'."
    
    # Finally release lock and exist normally.
    release_lock()
    sys.exit(0)

