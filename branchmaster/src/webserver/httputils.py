def generic_malformed_request(httphandler):
    httphandler.send_response(200)
    httphandler.send_header("Content-type", "text/html")
    httphandler.end_headers()

    httphandler.write_answer_encoded("<html>")
    httphandler.write_answer_encoded("<h1> Request failed. </h1>")
    httphandler.write_answer_encoded("<p> The server received a malformed request. </p>")
    httphandler.write_answer_encoded("</html>")

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
