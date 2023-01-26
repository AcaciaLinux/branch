import cgi
import os
import json
import traceback
import functools

from enum import Enum
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from webserver import endpoints
from functools import wraps

WEB_CONFIG = {
    "web_debug": False,
    "logger_function_debug": print,
    "logger_function_info": print,
    "send_cors_headers": False
}

#
# endpoint class with path and corresponding handler function
#
class endpoint():
    def __init__(self, path, handler):
        self.path = path
        self.handlerfunc = handler

#
# webstatus Enum
#
class webstatus(Enum):
    SUCCESS = 200
    MISSING_DATA = 300
    SERV_FAILURE = 400
    AUTH_FAILURE = 500

#
# webresponse class
#
class webresponse():
    
    def __init__(self, wstatus, payload):
        self.status = wstatus.name
        self.response_code = wstatus.value
        self.payload = payload

    # WebResponse as json string
    def json_str(self):
        return json.dumps({ 
            "status": self.status,
            "response_code": self.response_code,
            "payload": self.payload
        })



class web_server(BaseHTTPRequestHandler):
    #
    # Overwrite BaseHTTPRequestHandler to logger_function
    #
    def log_message(self, format, *args):
        WEB_CONFIG["logger_function_info"]("[branchweb] {}".format(*args))

    # List of currently active HTTPSessions
    active_sessions = [ ]
    
    #
    # Static Endpoint register for all
    # HTTPHandler instances
    #
    get_endpoints = [ ]
    post_endpoints = [ ]

    #
    # Registers a GET function to the webserver
    # Takes a dict:
    # path -> handler_func
    #
    @staticmethod
    def register_get_endpoints(get_dict):
        for path in get_dict:
            WEB_CONFIG["logger_function_debug"]("Registered GET endpoint for path: {}".format(path))
            web_server.get_endpoints.append(endpoint(path, get_dict[path]))
    #
    # Registers a POST function to the webserver
    # Takes a dict:
    # path -> handler_func
    #
    @staticmethod
    def register_post_endpoints(post_dict):
        for path in post_dict:
            WEB_CONFIG["logger_function_debug"]("Registered POST endpoint for path: {}".format(path))
            web_server.post_endpoints.append(endpoint(path, post_dict[path]))

    #
    # Parse a HTTP-get form
    #
    @staticmethod
    def parse_form_data(str_form):
        form_val = str_form.split("&")

        _dict = { }

        for dataset in form_val:
            split = dataset.split("=")
            if(not "=" in dataset):
                continue

            key = split[0]
            val = split[1]
            _dict[key] = val

        return _dict

    #
    # fetches the real path from 
    #
    def fetch_real_path(self):
        # strip /
        self.path = self.path[1:len(self.path)]        
        form_dict = None

        if(self.path):
            # if char 0 is ? we have form data to parse
            if(self.path[0] == '?' and len(self.path) > 1):
                form_dict = web_server.parse_form_data(self.path[1:len(self.path)])
                if(not form_dict is None):
                    lk = list(form_dict.keys())
                    if(len(lk) == 0):
                        return None
                    else:
                        real_path = lk[0]
            else:
                real_path = self.path
        else:
            real_path = self.path
         
        return real_path, form_dict


    #
    # End HTTPHeaders
    #
    def end_headers(self):
        if(WEB_CONFIG["send_cors_headers"]):
            WEB_CONFIG["logger_function_info"]("Sending Wildcard CORS headers.")
            WEB_CONFIG["logger_function_info"]("This should only be used for debugging purposes.")

            self.send_header('Access-Control-Allow-Origin', "*")
            self.send_header('Access-Control-Allow-Methods', "*")
            self.send_header('Access-Control-Allow-Headers', "*")
        return super(web_server, self).end_headers()

    #
    # Encode a string as a byte-list and send it
    # to the current HTTPHandler
    #
    def write_answer_encoded(self, message):
        WEB_CONFIG["logger_function_debug"]("Sending message: {}".format(message))
        self.wfile.write(bytes(message, "utf-8"))

    #
    # send web response
    #
    def send_web_response(self, status, payload):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.write_answer_encoded(webresponse(status, payload).json_str())

    #
    # send a raw string response without wrapping it in a webresponse object 
    #
    def send_str_raw(self, http_status, msg):
        self.send_response(http_status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.write_answer_encoded(msg)
    
    #
    # send a file response to the current http handler
    # 
    def send_file(self, file, file_len, file_name):
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Length", file_len)
        self.send_header("Content-Disposition", "filename=\"" + file_name + "\"")
        self.end_headers()

        while True:
            bytes_read = file.read(4096)

            if(not bytes_read):
                break

            self.wfile.write(bytes_read)

    #
    # send generic malformed request response
    #
    def generic_malformed_request(self):
        self.send_web_response(webstatus.SERV_FAILURE, "Bad Request.")

    # 
    # handle the get request
    #
    def do_GET(self):
        WEB_CONFIG["logger_function_info"]("Handling API-get request from {}..".format(self.client_address))

        real_path, form_dict = self.fetch_real_path()
        if(real_path is None):
            self.send_web_response(webstatus.SERV_FAILURE, "Bad request.")
            return
        
        no_match = True
        for endpoint in web_server.get_endpoints:
            if(endpoint.path == real_path):
                # handle
                try:
                    endpoint.handlerfunc(self, form_dict)
                    no_match = False
                except Exception as ex:
                    WEB_CONFIG["logger_function_info"]("Exception raised in endpoint function for {}: {}".format(real_path, ex))
                    WEB_CONFIG["logger_function_info"]("Errors from the webserver are not fatal to the masterserver.")
                    WEB_CONFIG["logger_function_info"]("Connection reset.")
                    
                    if(WEB_CONFIG["webdebug"]):
                        WEB_CONFIG["logger_function_debug"]("Stacktrace:")
                        traceback.print_exc()

                    self.send_web_response(webstatus.SERV_FAILURE, "Internal server error.")

        if(no_match):
            self.send_web_response(webstatus.SERV_FAILURE, "Bad request.")

        return

    #
    # handle a post request
    #
    def do_POST(self):
        WEB_CONFIG["logger_function_info"]("Handling API-post request from {}..".format(self.client_address))

        real_path, form_dict = self.fetch_real_path()
        if(real_path is None):
            self.send_web_response(webstatus.SERV_FAILURE, "Bad request.")
            return
        
        # no post body, bad request.
        if(self.headers["Content-Length"] is None):
            self.send_web_response(webstatus.SERV_FAILURE, "Bad request.")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type']
            }
        )

        post_data = {}
        for f_obj in form.list:
            post_data[f_obj.name] = f_obj.value
       
        no_match = True
        for endpoint in web_server.post_endpoints:
            if(endpoint.path == real_path):
                # handle
                try:
                    endpoint.handlerfunc(self, form_dict, post_data)
                    no_match = False
                except Exception as ex:
                    WEB_CONFIG["logger_function_info"]("Exception raised in endpoint function for {}: {}".format(real_path, ex))
                    WEB_CONFIG["logger_function_info"]("Errors from the webserver are not fatal to the masterserver.")
                    WEB_CONFIG["logger_function_info"]("Connection reset.")
                    
                    if(WEB_CONFIG["webdebug"]):
                        WEB_CONFIG["logger_function_debug"]("Stacktrace:")
                        traceback.print_exc()

                    self.send_web_response(webstatus.SERV_FAILURE, "Internal server error.")

        if(no_match):
            self.send_web_response(webstatus.SERV_FAILURE, "Bad request.")

        return 

#
# stub class of ThreadedHTTPServer
#
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

#
# Start the webserver
#
def start_web_server(hostname, serverport):
    web_serv = None
   
    try:
        web_serv = ThreadedHTTPServer((hostname, serverport), web_server)
        web_serv.serve_forever()
    except Exception as ex:
        WEB_CONFIG["logger_function_info"]("Webserver failed to initialize: {}".format(ex))
        WEB_CONFIG["logger_function_info"]("Thread exiting.")
        return
