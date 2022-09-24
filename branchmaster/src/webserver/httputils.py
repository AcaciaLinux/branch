def send_error_response(httphandler, http_status, error_msg):
    httphandler.send_response(http_status)
    httphandler.send_header("Content-type", "text/html")
    httphandler.end_headers()
    httphandler.write_answer_encoded(error_msg)

def generic_malformed_request(httphandler):
    httphandler.send_response(400)
    httphandler.send_header("Content-type", "text/html")
    httphandler.end_headers()
    httphandler.write_answer_encoded("E_REQUEST")


def send_file(httphandler, file):
    httphandler.send_response(200)

    # Content-type: application/octet-stream
    httphandler.send_header("Content-type", "application/octet-stream")
    httphandler.end_headers()

    while True:
        bytes_read = file.read(4096)

        if(not bytes_read):
            break

        httphandler.wfile.write(bytes_read)
