#!/usr/bin/env python

from twisted.web import proxy, http, server, resource
from twisted.internet import reactor
from twisted.python import log

import sys
import re
import base64

import db


log.startLogging(sys.stdout)
web_port = 8080
proxy_port = 8001


class BlockingProxyRequest(proxy.ProxyRequest):
    def extract_user(self):
        ''' Extract user from headers '''
        hs = self.received_headers
        try:
            auth = hs['proxy-authorization']
            decoded = base64.decodestring(auth.rsplit(' ', 1)[-1])
            return decoded.rsplit(':', 1)[0]
        except KeyError:
            return None

    def process(self):
        ''' Process request, filtered according to blacklist '''
        user = self.extract_user()

        # Require authentication
        if not user:
            for line in ('HTTP/1.1 407 Proxy Authentication Required\r\n',
                         'Proxy-Authenticate: basic realm="torquemada"\r\n',
                         'Content-Type: text/html\r\n',
                         '\r\n',
                         'Unauthorized.\r\n'):
                self.transport.write(line)
            self.transport.loseConnection()
            return

        # Add torquedama user as X-header
        host = self.received_headers['host']
        if re.match(r'(localhost|127\.0\.0\.1):%i' % web_port, host):
            self.requestHeaders.addRawHeader('x-torquemada-user', user)

        # Check uri against blacklist
        if db.blocking_regex(user).search(self.uri):
            log.msg("blocked: %s" % self.uri)
            self.transport.write("HTTP/1.0 200 OK\r\n")
            self.transport.write("Content-Type: text/html\r\n")
            self.transport.write("\r\n")
            self.transport.write('''<H1>BLOCKED</H1>''')
            self.transport.loseConnection()
        else:
            proxy.ProxyRequest.process(self)


class BlockingProxy(proxy.Proxy):
    requestFactory = BlockingProxyRequest


class ProxyFactory(http.HTTPFactory):
    protocol = BlockingProxy

    def __init__(self):
        http.HTTPFactory.__init__(self)


class Simple(resource.Resource):
    isLeaf = True

    def extract_user(self, request):
        ''' Extract torquemada user name from headers '''
        return request.received_headers.get('x-torquemada-user', None)

    def render_POST(self, request):
        ''' Handle POST '''
        user = self.extract_user(request)
        if user:
            if 'lists' in request.args or len(request.args['lists']) == 0:
                lists = map(str.strip,
                            request.args['lists'][0].split('\n'))
                for lst in filter(len, lists):
                    db.add_list(user, lst)
        return self.render_GET(request)

    def render_GET(self, request):
        ''' Handle GET '''
        user = self.extract_user(request)
        if user:
            return '''
            <html><body>
            User: %s<br/>
            Lists: %s<br/>
            <form method="post">
              <textarea name="lists"></textarea>
              <input type="submit">
            </form>
            </body></html>
            ''' % (user, ','.join(db.user_lists(user)))
        else:
            return '''
            <html><body>Please login</body></html>
            '''

# Prepare webserver
site = server.Site(Simple())

# Add listeners
reactor.listenTCP(proxy_port, ProxyFactory())
reactor.listenTCP(web_port, site)

# Run event-loop
reactor.run()
