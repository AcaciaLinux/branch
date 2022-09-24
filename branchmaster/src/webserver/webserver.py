from http.server import BaseHTTPRequestHandler, HTTPServer

from log import blog

#
# Registered HTTP endpoints
#
endpoint_register = [ ]

#
# Register API endpoint
#
def register_endpoint(endpoint):
    blog.debug("Registered endpoint for path: {}".format(endpoint.path))
    endpoint_register.append(endpoint)

#
# Remove API endpoint
#
def remove_endpoint(endpoint):
    endpoint_register.remove(endpoint)

#
# Web Server class
#
class web_server(BaseHTTPRequestHandler):

    # stub out http.server log messages
    def log_message(self, format, *args):
        pass


    def write_answer_encoded(self, message):
        self.wfile.write(bytes(message, "utf-8"))

    # 
    # handle the get request
    #
    def do_GET(self):
        blog.web_log("Handling API request from {}..".format(self.client_address))

        # strip /
        self.path = self.path[1:len(self.path)]        

        form_dict = None
        real_path = "" 

        if(self.path):
            # if char 0 is ? we have form data to parse
            if(self.path[0] == '?' and len(self.path) > 1):
                form_dict = parse_form_data(self.path[1:len(self.path)])
                if(not form_dict is None):
                    real_path = list(form_dict.keys())[0]
            else:
                real_path = self.path
        else:
            real_path = self.path

        for endpoint in endpoint_register:
            if(endpoint.path == real_path):
                # handle
                try:
                    endpoint.handlerfunc(self, form_dict)
                    return
                except Exception as ex:
                    blog.warn("Exception raised in endpoint function for {}: {}".format(real_path, ex))
                    blog.warn("Errors from the webserver are not fatal to the masterserver.")
                    blog.warn("Connection reset.")
                    return
        
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
    
        self.write_answer_encoded("E_REQUEST")
        return


def parse_form_data(str_form):
    form_val = str_form.split("&")

    if(not "=" in str_form):
        return None

    _dict = { }

    for dataset in form_val:
        split = dataset.split("=")
        key = split[0]
        val = split[1]
        _dict[key] = val

    return _dict


def start_web_server(hostname, serverport):
    web_serv = HTTPServer((hostname, serverport), web_server)

    # We don't handle keyboardInterrupt for the webserver,
    # it's killed once the main thread exits
    try:
        web_serv.serve_forever()
    except KeyboardInterrupt:
        pass

    web_serv.server_close()
