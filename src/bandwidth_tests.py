from abc import ABC, abstractmethod
from typing import List

import signal
from mininet.log import output
from mininet.net import Mininet

class BandwidthTest(ABC):

    registered_tests = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'test_id'):
            raise TypeError(f"Can't instantiate bandwidth test subclass {cls.__name__} without test_id attribute")
        if cls.test_id in BandwidthTest.registered_tests:
            raise ValueError(f"Bandwidth test with test_id {cls.test_id} already exists")
        if not hasattr(cls, 'description'):
            raise TypeError(f"Can't instantiate bandwidth test subclass {cls.__name__} without description attribute")
        BandwidthTest.registered_tests[cls.test_id] = cls

    @staticmethod
    def get_test_ids() -> List[str]:
        return list(BandwidthTest.registered_tests.keys())
    
    @staticmethod
    def get_description(test_id: str):
        test = BandwidthTest.registered_tests.get(test_id)
        if not test:
            print(f"Test with test_id {test_id} not found")
            return
        return test.description

    @staticmethod
    def run_test(test_id: str, mn: Mininet, line: str):
        test = BandwidthTest.registered_tests.get(test_id)
        if not test:
            print(f"Test with test_id {test_id} not found")
            return
        output(f"- {test.description}\n")
        test._run_test(mn, line)

    @classmethod
    @abstractmethod
    def _run_test(cls, mn: Mininet, line: str):
        pass

    @staticmethod
    def run_with_timeout(timeout: int, fun: callable):
        """
        Run a function with a timeout
        :param timeout: the timeout in seconds
        :param fun: the function to run
        :return: the result of the function
        """
        def handler(signum, frame):
            raise TimeoutError("Bandwidth test timed out")

        signal.signal(signal.SIGALRM, handler)
        signal.alarm(timeout)

        try:
            return fun()
        except TimeoutError as e:
            output(f"Bandwidth test timed out\n")
        finally:
            signal.alarm(0)


class BandwidthTest1(BandwidthTest):
    test_id = "1"
    description = "Test 1 description"

    @classmethod
    def _run_test(cls, mn: Mininet, line: str):
        server = mn.getNodeByName("h3")
        client = mn.getNodeByName("h1")

        def test():
            return mn.iperf((client, server), l4Type='UDP', udpBw='20M', seconds=10, port=9999)
        
        result = cls.run_with_timeout(15, test)
        output(f"Bandwidth test result: {result}\n")


class BandwidthTest2(BandwidthTest):
    test_id = "2"
    description = "Test 2 description"

    @classmethod
    def _run_test(cls, mn: Mininet, line: str):
        server = mn.getNodeByName("h3")
        client = mn.getNodeByName("h1")

        def test():
            return mn.iperf((client, server), l4Type='UDP', udpBw='20M', seconds=10, port=9997)
        
        result = cls.run_with_timeout(15, test)
        output(f"Bandwidth test result: {result}\n")


class BandwidthTest3(BandwidthTest):
    test_id = "3"
    description = "Test 3 description"

    @classmethod
    def _run_test(cls, mn: Mininet, line: str):
        server = mn.getNodeByName("h3")
        client = mn.getNodeByName("h1")

        def test():
            return mn.iperf((client, server), l4Type='UDP', udpBw='20M', seconds=10, port=9997)
        
        result = cls.run_with_timeout(15, test)
        output(f"Bandwidth test result: {result}\n")
