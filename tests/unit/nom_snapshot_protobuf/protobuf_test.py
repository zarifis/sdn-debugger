from nom_snapshot_protobuf.nom_snapshot_pb2 import *
import unittest
import sys
import os.path
import itertools
from copy import copy
import types

sys.path.append(os.path.dirname(__file__) + "/../../..")

class protobuf_test(unittest.TestCase):
    def test_basic(self):
        test_action = Action(type=Action.output, port=2)
        test_match = Match(field=Match.dl_src, polarity=False, values=[1])
        test_rule = Rule(match=test_match, actions=[test_action])
        test_switch = Switch(dpid=1, rules=[test_rule])
        test_host = Host(mac="00:00:00:00:00:00")

if __name__ == '__main__':
  unittest.main()