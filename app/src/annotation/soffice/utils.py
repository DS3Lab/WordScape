import socket

import psutil
from typing import Union

__all__ = [
    "get_soffice_process_on_port",
    "get_free_port"
]


def get_soffice_process_on_port(port) -> Union[psutil.Process, None]:
    """ function returns the soffice process object on the given port or
    None if no process is running on the given port.
    """
    for proc in psutil.process_iter():
        try:
            name = proc.name()
        except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
        ):
            continue

        if not name.startswith("soffice"):
            continue

        try:
            connections = proc.connections()
        except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess
        ):
            continue

        for conn in connections:
            if (
                    conn.status == psutil.CONN_LISTEN and
                    conn.laddr.port == port
            ):
                return proc

    return None


def get_free_port():
    r""" function returns a free port on the current machine """
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
