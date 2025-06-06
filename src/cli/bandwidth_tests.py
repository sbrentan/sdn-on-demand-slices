from abc import ABC, abstractmethod
from typing import List

import signal
from mininet.log import output
from mininet.net import Mininet

from common import PacketInfo

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
    def run_test(test_id: str, mn: Mininet, line: str = None, packet_info: PacketInfo = None):
        if test_id is None:
            if packet_info is None:
                print("No test_id or packet_info provided")
                return
            src_host = [h for h in mn.hosts if h.MAC() == packet_info['src_mac']][0]
            dst_host = [h for h in mn.hosts if h.MAC() == packet_info['dst_mac']][0]
            result = BandwidthTest.start_bandwidth_test(src_host, dst_host, packet_info['protocol'], packet_info['dst_port'])

            output(f"Bandwidth test result:\n{result}\n")
        else:
            test = BandwidthTest.registered_tests.get(test_id)
            if not test:
                print(f"Test with test_id {test_id} not found")
                return
            output(f"- {test.description}\n")
            test._run_test(mn, line)

    @staticmethod
    def start_bandwidth_test(src_host, dst_host, protocol, dst_port):
        """
        Start a bandwidth test between two hosts
        :param src_host: the source host
        :param dst_host: the destination host
        :param protocol: the protocol to use (TCP or UDP)
        :param dst_port: the destination port
        """
        def test():
            proto_str = "-u -b 1000M" if protocol == "UDP" else ""
            dst_host.sendCmd(f"iperf -s {proto_str} -p {dst_port} -t 15")
            src_host.sendCmd(f"iperf -c {dst_host.IP()} {proto_str} -p {dst_port} -t 10 -i 1")
            result = src_host.waitOutput()
            server_out = dst_host.waitOutput()
            if server_out:
                output(f"\n{server_out}\n")
            return result
            
        result = BandwidthTest.run_with_timeout(30, test)
        if result is None:
            src_host.sendCmd("pkill iperf")
            dst_host.sendCmd("pkill iperf")
            src_host.waitOutput()
            dst_host.waitOutput()
        return result

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


# class BandwidthTest1(BandwidthTest):
#     test_id = "1"
#     description = "Test 1 description"

#     @classmethod
#     def _run_test(cls, mn: Mininet, line: str):
#         server = mn.getNodeByName("h3")
#         client = mn.getNodeByName("h1")

#         def test():
#             return cls.start_bandwidth_test(client, server, 'UDP', 9999)
        
#         result = cls.run_with_timeout(15, test)
#         output(f"Bandwidth test result: {result}\n")
