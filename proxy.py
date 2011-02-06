#!/usr/bin/env python

from twisted.web import proxy, http
from twisted.internet import reactor
from twisted.python import log

import sys
import re
import base64

log.startLogging(sys.stdout)

blacklist = None
authed = False


class BlockingProxyRequest(proxy.ProxyRequest):
    def get_user(self):
        hs = self.received_headers
        try:
            auth = hs['proxy-authorization']
            decoded = base64.decodestring(auth.rsplit(' ', 1)[-1])
            return decoded.rsplit(':', 1)[0]
        except KeyError:
            return None

    def process(self):
        user = self.get_user()
        if not user:
            for line in ('HTTP/1.1 407 Proxy Authentication Required\r\n',
                         'Proxy-Authenticate: basic realm="torquemada"\r\n',
                         'Content-Type: text/html\r\n',
                         '\r\n',
                         'Unauthorized.\r\n'):
                print line
            self.transport.loseConnection()
            return

        log.msg('user: %s' % user)
        log.msg('%s %s' % (self.uri, blacklist.search(self.uri)))

        if blacklist.search(self.uri):
            print "Blocked:", self.uri
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
        self.load_rules()

    def load_rules(self):
        log.msg('loading ad rules')
        groups = []
        for line in file('easylist.txt'):
            if '!' in line or '||' in line or '#' in line:
                continue
            line = line.strip()
            line = re.escape(line)
            if line[0:1] == r'\|':
                line = '^%s' % line[2:]
            if line[-2:] == '\|':
                line = '%s$' % line[:-2]
            groups.append(line)
        global blacklist
        blacklist = re.compile('|'.join(groups), re.I)
        log.msg('%i rules loaded' % len(groups))

reactor.listenTCP(8001, ProxyFactory())
reactor.run()
