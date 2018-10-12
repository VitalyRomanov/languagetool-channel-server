from http.server import BaseHTTPRequestHandler
import re
from copy import copy


def extractId(request):
    m = re.search('reqid=[0-9]{1,}', request)
    if m:
        idField = m.group()
        req = copy(request).replace(idField, '')
        reqid = idField.split("=")[1]
        return req, reqid
    return None


def LTRequestHandler(queue):

    class LTChannelHandler(BaseHTTPRequestHandler):
        # q = queue
        # LT_ADDR = LT_ADDR
        # LT_PORT = LT_PORT

        def __init__(self, *args, **kwargs):
             super(LTChannelHandler, self).__init__(*args, **kwargs)
             
            #  self.q = queue
            #  self.LT_ADDR = LT_ADDR
            #  self.LT_PORT = LT_PORT
        
        def do_HEAD(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

        def do_GET(self):
            request = self.path.split("/")

            req_reqid = extractId(self.path)

            # Check whether the requies is compliant with LT
            valid = False
            if len(request) == 3:
                if request[1] == 'v2' and req_reqid is not None:
                    valid = True

            if valid:
                self.respond({'status': 200}, 'OK')
                queue.put(req_reqid)
                # queue.put("http://{}:{}{}".format(LT_ADDR, LT_PORT, self.path))
            else:
                self.respond({'status': 500}, 'Check resquest format')
            

        def handle_http(self, status_code, path, message):
            self.send_response(status_code)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            m = message if status_code==200 else "{}: {}".format(message, path)
            content = '''
            {}
            '''.format(m)
            # print(content)
            return bytes(content, 'UTF-8')

        def respond(self, opts, message):
            response = self.handle_http(opts['status'], self.path, message)
            self.wfile.write(response)

    return LTChannelHandler
