from twisted.web import proxy, http
from twisted.internet import reactor
from twisted.python import log

import sys
import re

log.startLogging(sys.stdout)

blacklist = None


class BlockingProxyRequest(proxy.ProxyRequest):
    def process(self):
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
            groups.append(re.escape(line.strip()).replace(r'\*', '.*'))
        global blacklist
        blacklist = re.compile('|'.join(groups), re.I)
        log.msg('%i rules loaded' % len(groups))

reactor.listenTCP(8001, ProxyFactory())
reactor.run()
