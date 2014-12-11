# -*- test-case-name: twisted.tube.test.test_undefer -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.tubes.undefer}.
"""

from twisted.trial.unittest import SynchronousTestCase
from twisted.internet.defer import succeed
from twisted.tubes.undefer import deferredToResult
from twisted.internet.defer import Deferred
from twisted.tubes.test.util import FakeDrain
from twisted.tubes.test.util import FakeFount
from twisted.tubes.tube import tube, series

class DeferredIntegrationTests(SynchronousTestCase):
    """
    Tests for L{deferredToResult}.
    """
    def setUp(self):
        """
        Create a fount and drain.
        """
        self.ff = FakeFount()
        self.fd = FakeDrain()


    def test_tubeYieldsFiredDeferred(self):
        """
        When a tube yields a fired L{Deferred} its result is synchronously
        delivered.
        """

        @tube
        class SucceedingTube(object):
            def received(self, data):
                yield succeed(''.join(reversed(data)))

        fakeDrain = self.fd
        self.ff.flowTo(series(SucceedingTube(), deferredToResult())).flowTo(fakeDrain)
        self.ff.drain.receive("hello")
        self.assertEquals(self.fd.received, ["olleh"])


    def test_tubeYieldsUnfiredDeferred(self):
        """
        When a tube yields an unfired L{Deferred} its result is asynchronously
        delivered.
        """

        d = Deferred()

        @tube
        class WaitingTube(object):
            def received(self, data):
                yield d

        fakeDrain = self.fd
        self.ff.flowTo(series(WaitingTube(), deferredToResult())).flowTo(fakeDrain)
        self.ff.drain.receive("ignored")
        self.assertEquals(self.fd.received, [])

        d.callback("hello")

        self.assertEquals(self.fd.received, ["hello"])


    def test_tubeYieldsMultipleDeferreds(self):
        """
        When a tube yields multiple deferreds their results should be delivered
        in order.
        """

        d = Deferred()

        @tube
        class MultiDeferredTube(object):
            didYield = False
            def received(self, data):
                yield d
                MultiDeferredTube.didYield = True
                yield succeed("goodbye")

        fakeDrain = self.fd
        self.ff.flowTo(series(MultiDeferredTube(), deferredToResult())).flowTo(fakeDrain)
        self.ff.drain.receive("ignored")
        self.assertEquals(self.fd.received, [])

        d.callback("hello")

        self.assertEquals(self.fd.received, ["hello", "goodbye"])


    def test_tubeYieldedDeferredFiresWhileFlowIsPaused(self):
        """
        When a L{Tube} yields an L{Deferred} and that L{Deferred} fires when
        the L{_SiphonFount} is paused it should buffer it's result and deliver
        it when L{_SiphonFount.resumeFlow} is called.
        """
        d = Deferred()

        @tube
        class DeferredTube(object):
            def received(self, data):
                yield d

        fakeDrain = self.fd
        self.ff.flowTo(series(DeferredTube(), deferredToResult())).flowTo(fakeDrain)
        self.ff.drain.receive("ignored")

        anPause = self.fd.fount.pauseFlow()

        d.callback("hello")
        self.assertEquals(self.fd.received, [])

        anPause.unpause()
        self.assertEquals(self.fd.received, ["hello"])


