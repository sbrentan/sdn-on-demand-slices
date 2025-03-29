from typing import TypedDict


class PacketInfo(TypedDict):
    """TypedDict for packet information."""
    protocol: str
    src_port: int
    dst_port: int
    src_mac: str
    dst_mac: str
