#!/usr/bin/env python
# Reflects the requests from HTTP methods GET, POST, PUT, and DELETE
# Written by Nathan Hamiel (2010)

from http.server import HTTPServer, BaseHTTPRequestHandler
from optparse import OptionParser


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):

        request_path = self.path

        print("\n----- Request Start ----->\n")
        print(request_path)
        print(self.headers)
        print("<----- Request End -----\n")

        guard = self.headers.get("really-important-header")
        if guard and str(guard) == "some-really-important-value":
            print("guard header set")
        self.send_response(200)
        self.send_header("Set-Cookie", "foo=bar")

    def do_POST(self):

        request_path = self.path

        print("\n----- Request Start ----->\n")
        print(request_path)

        request_headers = self.headers
        content_length = request_headers.get("content-length")
        length = int(content_length) if content_length else 0

        guard = request_headers.get("really-important-header")
        if guard and str(guard) == "some-really-important-value":
            print(request_headers)
            content = self.rfile.read(length)
            print(content[0])
            with open("backstop_dump.png", "wb") as wfile:
                wfile.write(content)
            print("<----- Request End -----\n")
        else:
            print("guard header not set")

        self.send_response(200)

    do_PUT = do_POST
    do_DELETE = do_GET


def main():
    port = 9000
    print("Listening on localhost:%s" % port)
    server = HTTPServer(("", port), RequestHandler)
    server.serve_forever()


if __name__ == "__main__":
    parser = OptionParser()
    parser.usage = (
        "Creates an http-server that will echo out any GET or POST parameters\n"
        "Run:\n\n"
        "   reflect"
    )
    (options, args) = parser.parse_args()

    main()
