import time
import json
import urllib.request
from http.server import HTTPServer
from LTRequestHandler import LTRequestHandler
from threading import Thread, current_thread
from time import sleep
from queue import Queue
from pprint import pprint
import ssl
from os.path import isfile
from configparser import ConfigParser
# import sys


if not isfile("server.conf"):
    raise FileNotFoundError("Provide configuration file 'server.conf'")


config = ConfigParser()
config.read('server.conf')

print("\nReading configs...")
NUM_WORKERS = int(config['SETTINGS']['NUM_WORKERS'])
MIDDLE_SERVER_HOST = config['SETTINGS']['MIDDLE_SERVER_HOST']
MIDDLE_SERVER_PORT = int(config['SETTINGS']['MIDDLE_SERVER_PORT'])
LT_ADDR = config['SETTINGS']['LT_ADDR']
LT_PORT = int(config['SETTINGS']['LT_PORT'])
RESPONSE_URL = config['SETTINGS']['RESPONSE_URL']
print("NUM_WORKERS: ", NUM_WORKERS)
print("MIDDLE_SERVER_HOST: ", MIDDLE_SERVER_HOST)
print("MIDDLE_SERVER_PORT: ", MIDDLE_SERVER_PORT)
print("LT_ADDR: ", LT_ADDR)
print("LT_PORT: ", LT_PORT)
print("RESPONSE_URL: ", RESPONSE_URL)
print("\n\n")


ssl._create_default_https_context = ssl._create_unverified_context


def lt(worker_name, reqid, requestLink, reqData):
    """
    :param requestLink: fully formed LT request link
    :return: the result of LT check
    """
    print(time.asctime(), "Sending request to LT for reqid {} from worker {}".format(reqid, worker_name))
    # url_addr = requestLink
    # data = None
    # with urllib.request.urlopen(url_addr) as url:
    #     data = json.loads(url.read().decode())

    if reqData:
        url_addr = requestLink
        enc_json = json.dumps(reqData).encode('utf-8')
        # print(enc_json)
        req = urllib.request.Request(url_addr, data=enc_json)#, headers={'content-type': 'application/json'})

        # def pretty_print_POST(req):
        #     """
        #     At this point it is completely built and ready
        #     to be fired; it is "prepared".
        #
        #     However pay attention at the formatting used in
        #     this function because it is programmed to be pretty
        #     printed and may differ from the actual request.
        #     """
        #     print('{}\n{}\n{}\n\n{}'.format(
        #         '-----------START-----------',
        #         req.method + ' ' + req.url,
        #         '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
        #         req.body,
        #     ))
        #
        # pretty_print_POST(req)
    else:
        req = requestLink

    data = None
    with urllib.request.urlopen(req) as url:
        data = json.loads(url.read().decode())

    print(time.asctime(), "Received responce from LT for reqid {} from worker {}".format(reqid, worker_name))

    return data


def postLTCheck(worker_name, reqid, checkResult):
    print(time.asctime(), "Sending response for reqid {} from worker {}".format(reqid, worker_name))
    url_addr = RESPONSE_URL
    enc_json = json.dumps(checkResult).encode('utf-8')
    req = urllib.request.Request(url_addr, data=enc_json,
                                 headers={'content-type': 'application/json'})
    response = urllib.request.urlopen(req)
    print(time.asctime(), "Sent response for reqid {} from worker {}: ".format(reqid, worker_name), response.read())


def strip_answ(answ):
    stripped = {'matches':[]}
    for match in answ['matches']:
        m = {field: match[field] for field in ['message', 'offset', 'length', 'replacements']}
        m['rule'] = {'id': match['rule']['id']}

        stripped['matches'].append(m)

    return stripped


def do_work(request, worker_name):
    """
    :param request: request string passed by the client
    :return: Nothing
    Substitute the address for LT, get the check result and post it back to client
    """
    req, reqid = request

    if type(req) is dict:
        reqLink = "http://{}:{}/v2/check".format(LT_ADDR, LT_PORT)
        reqData = req
    elif type(req) is str:
        reqLink = "http://{}:{}{}".format(LT_ADDR, LT_PORT, req)
        reqData = None

    answ = lt(worker_name, reqid, reqLink, reqData)
    stripped = strip_answ(answ)
    stripped['reqid'] = reqid
    # pprint(stripped)
    postLTCheck(worker_name, reqid, stripped)


def worker(queue):
    worker_name = current_thread().name
    while True:
        req = queue.get()
        try:
            do_work(req, worker_name)
        except Exception as e:
            print("Exception while processing: ", req)
            print(e)
        queue.task_done()
        sleep(1)

if __name__ == '__main__':
    qObj = Queue()

    for i in range(NUM_WORKERS):
        t = Thread(target=worker, args=(qObj,))
        t.daemon = True
        t.start()

    server_class = HTTPServer
    httpd = server_class((MIDDLE_SERVER_HOST, MIDDLE_SERVER_PORT), LTRequestHandler(qObj))
    print(time.asctime(), 'Server Starts - %s:%s' % (MIDDLE_SERVER_HOST, MIDDLE_SERVER_PORT))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass

    qObj.join()
    httpd.server_close()
    print(time.asctime(), 'Server Stops - %s:%s' % (MIDDLE_SERVER_HOST, MIDDLE_SERVER_PORT))
