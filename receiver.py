# code from http://github.com/mariano/pyfire/blob/master/pyfire/twistedx/receiver.py
import tempfile

from twisted.internet import protocol
from twisted.web import client

class StringReceiver(protocol.Protocol):
    """ String receiver protocol. To be used in combination
    with producer to upload files in a twisted python way

    """
    buffer = ""

    def __init__(self, deferred=None):
        self._deferred = deferred
        self.code = 0
        self.buffer = tempfile.NamedTemporaryFile(prefix='melisi-',
                                                  suffix='.tmp')

    def dataReceived(self, data):
        """ Receives data. We don't expect a lot of data here
        so we store result directly into memory
        """
        self.buffer.write(data)

    def connectionLost(self, reason):
        self.buffer.seek(0)

        if self.code >= 200 and self.code < 300:
            self._deferred.callback(self.buffer)
        else:
            self._deferred.errback(self.buffer)

        self.buffer.close()
