import pytest

from zeno.common.exceptions import InvalidSignature
from zeno.common.util import getlogger

from zeno.test.helper import TestNode
from zeno.test.malicious_behaviors_node import changesRequest, makeNodeFaulty
from zeno.test.node_request.node_request_helper import checkPropagated
from zeno.test.testing_utils import adict
from zeno.test.eventually import eventually

logger = getlogger()
whitelist = ['doing nothing for now',
             'InvalidSignature']


@pytest.fixture(scope="module")
def setup(nodeSet):
    gn = [v for k, v in nodeSet.nodes.items() if k != 'Alpha']
    # delay incoming client messages for good nodes by 250 milliseconds
    # this gives Alpha a chance to send a propagate message
    for n in gn:  # type: TestNode
        n.clientIbStasher.delay(lambda _: 1)
    return adict(goodNodes=gn)


@pytest.fixture(scope="module")
def evilAlpha(nodeSet):
    makeNodeFaulty(nodeSet.Alpha, changesRequest)


faultyNodes = 1


def testOneNodeAltersAClientRequest(looper,
                                    nodeSet,
                                    setup,
                                    evilAlpha,
                                    sent1):
    checkPropagated(looper, nodeSet, sent1, faultyNodes)

    goodNodes = setup.goodNodes

    def check():
        for node in goodNodes:

            # ensure the nodes are suspicious of Alpha
            params = node.spylog.getLastParams(TestNode.reportSuspiciousNode)
            frm = params["nodeName"]
            reason = params["reason"]
            assert frm == 'Alpha'
            assert isinstance(reason, InvalidSignature)

            # ensure Alpha's propagates were ignored by the other nodes
            key = sent1.clientId, sent1.reqId
            props = node.requests[key].propagates
            assert 'Alpha' not in props
            for good in goodNodes:
                assert good.name in props

    looper.run(eventually(check, retryWait=1, timeout=10))