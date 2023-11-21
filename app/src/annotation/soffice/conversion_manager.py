from datetime import datetime as dt
import subprocess
from pathlib import Path
import platform
import psutil
import resource
import time
import logging

from src.annotation.soffice.utils import *
from src.annotation.config import AnnotationConfig
from src.exceptions import ConversionFailedException, SofficeStartFailed

if platform.system() == "Darwin":
    _SHELL_EXECUTABLE = "/bin/zsh"
elif platform.system() == "Linux":
    _SHELL_EXECUTABLE = "/bin/bash"
else:
    raise RuntimeError("Unsupported platform", platform.system())

UNOCONVERT_MAX_MEM = 2 * 1024 * 1024 * 1024  # 2GB


def get_limit_memory_func():
    if platform.system() == "Darwin":
        # macos
        return lambda: None
    elif platform.system() == "Linux":
        # linux
        return _limit_virtual_memory
    else:
        raise RuntimeError("Unsupported platform", platform.system())


def get_timestamp():
    return dt.now().isoformat()


def _limit_virtual_memory():
    resource.setrlimit(
        resource.RLIMIT_AS, (UNOCONVERT_MAX_MEM, UNOCONVERT_MAX_MEM)
    )


class ConversionManager:
    r""" Class manages the soffice process and provides methods to convert
    doc to docx files and docx files to pdf files.

    @param soffice_executable: path to the soffice executable
    @param config: annotation config object
    """

    def __init__(
            self, soffice_executable: str, config: AnnotationConfig,
            logger_name: str
    ):
        # init logger
        self.logger = logging.getLogger(name=logger_name)
        self.logger.setLevel(logging.DEBUG)

        # unoserver management
        self.soffice_executable = soffice_executable
        self.config = config
        self._soffice_listen_port = get_free_port()
        self.ip_address = "localhost"
        self._soffice_proc = self._start_unoserver()
        self._soffice_pid = self._soffice_proc.pid
        self._limit_mem_func = get_limit_memory_func()

    def _start_unoserver(self) -> psutil.Process:
        r""" function starts the soffice process on the given port. It waits
        until the process is running and returns the process object upon
        success. If the process could not be started, it raises an
        SofficeStartFailed exception.

        @return: the soffice process

        @raises: SofficeStartFailed, if the uno server could not be started
        """
        if get_soffice_process_on_port(
                port=self._soffice_listen_port
        ) is not None:
            raise RuntimeError(f"soffice process already running on "
                               f"port {self._soffice_listen_port}!")

        cmd = " ".join([
            "unoserver",
            f"--interface {self.ip_address}",
            f"--port {self._soffice_listen_port}",
            f"--executable {self.soffice_executable}",
            "--daemon"
        ])

        try:
            subprocess.run(
                cmd, shell=True, executable=_SHELL_EXECUTABLE,
                timeout=self.config.unoserver_start_timeout
            )
        except subprocess.TimeoutExpired:
            raise SofficeStartFailed(
                f"[Error=TimeoutExpired] Failed to start soffice @ "
                f"{self.ip_address}:{self._soffice_listen_port}"
            )

        self._ready = False

        t_end = time.time() + self.config.soffice_launch_timeout
        while time.time() < t_end:
            time.sleep(self.config.soffice_launch_ping_interval)
            soffice_proc = get_soffice_process_on_port(
                port=self._soffice_listen_port
            )

            if soffice_proc is not None:
                self.logger.info(
                    f"soffice(PID={soffice_proc.pid}) started @ "
                    f"{self.ip_address}:{self._soffice_listen_port}"
                )
                self._ready = True
                return soffice_proc

        raise SofficeStartFailed(
            f"Failed to start soffice @ "
            f"{self.ip_address}:{self._soffice_listen_port}"
        )

    def _maybe_restart_unoserver(self, force_restart=False):
        if not force_restart and self._is_running():
            return

        # make sure the process is killed
        self.shutdown_soffice()

        # soffice process has died, restart it
        self._xml_rpc_port = get_free_port()
        self._soffice_listen_port = get_free_port()
        self._soffice_proc = self._start_unoserver()
        self._soffice_pid = self._soffice_proc.pid

    def _is_running(self):
        """ function checks whether the soffice process is still running on the
        given port.
        """
        if self._soffice_proc is None:
            return False

        return self._soffice_proc.is_running()

    def shutdown_soffice(self):
        """ function kills the soffice process if it is still running. """
        self.logger.info(f"shutting down soffice process "
                         f"with pid {self._soffice_pid}")

        if self._soffice_proc is None:
            return

        if self._soffice_proc.is_running():
            self._soffice_proc.kill()
            time.sleep(1)

    def doc_to_docx(self, doc_fp: Path) -> Path:
        r""" function converts the given doc file to a docx file. It returns
        the path to the converted file.

        @param doc_fp: path to the doc file

        @raises: ConversionFailedException, if the conversion failed
        @raises: FileNotFoundError, if the given doc file does not exist
        """
        if not doc_fp.exists():
            raise FileNotFoundError(f"{doc_fp} does not exist")

        self._maybe_restart_unoserver(force_restart=False)

        tgt_fp = doc_fp.with_suffix(f".docx")

        cmd = " ".join([
            "unoconvert",
            str(doc_fp),
            str(tgt_fp),
            f"--convert-to docx",
            f"--interface {self.ip_address}",
            f"--port {self._soffice_listen_port}"
        ])

        try:
            proc = subprocess.Popen(
                cmd, shell=True, executable=_SHELL_EXECUTABLE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                preexec_fn=self._limit_mem_func
            )
            stdout, stderr = proc.communicate(
                timeout=self.config.unoconvert_timeout
            )

            if proc.returncode != 0:
                raise ConversionFailedException(
                    f"conversion of {doc_fp} to docx failed: "
                    f"stdout={stdout.decode('utf-8')}; "
                    f"stderr={stderr.decode('utf-8')}"
                )

        except subprocess.CalledProcessError:
            # process is likely dead, force restart
            self.logger.error("unoconvert failed; restarting soffice.")
            self._maybe_restart_unoserver(force_restart=True)
            proc = None
        except subprocess.TimeoutExpired:
            self.logger.error(f"unoconvert timeout; restarting soffice.")
            self._maybe_restart_unoserver(force_restart=True)
            proc = None
        except ConversionFailedException:
            self._maybe_restart_unoserver(force_restart=True)
            proc = None

        # remove source
        doc_fp.unlink(missing_ok=True)

        if proc is not None and proc.returncode == 0:
            return tgt_fp

        raise ConversionFailedException(
            f"conversion of {doc_fp} to docx failed"
        )

    def docx_to_pdf(self, doc_fp: Path) -> Path:
        r""" function converts the given docx file to a pdf file. It returns
        the path to the converted file.

        @param doc_fp: path to the docx file
        @return: path to the converted pdf file

        @raises: ConversionFailedException, if the conversion failed
        @raises: FileNotFoundError, if the given docx file does not exist
        """
        if not doc_fp.exists():
            raise FileNotFoundError(f"{doc_fp} does not exist")

        self._maybe_restart_unoserver(force_restart=False)

        tgt_fp = doc_fp.with_suffix(f".pdf")

        cmd = " ".join([
            "unoconvert",
            str(doc_fp),
            str(tgt_fp),
            f"--convert-to pdf",
            f"--interface {self.ip_address}",
            f"--port {self._soffice_listen_port}",
            f"--filter writer_pdf_Export"
        ])

        try:
            proc = subprocess.Popen(
                cmd, shell=True, executable=_SHELL_EXECUTABLE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                preexec_fn=self._limit_mem_func
            )
            stdout, stderr = proc.communicate(
                timeout=self.config.unoconvert_timeout
            )

            if proc.returncode != 0:
                raise ConversionFailedException(
                    f"conversion of {doc_fp} to docx failed: "
                    f"stdout={stdout.decode('utf-8')}; "
                    f"stderr={stderr.decode('utf-8')}"
                )
        except subprocess.CalledProcessError:
            # process is likely dead, force restart
            self.logger.error("unoconvert failed; restarting soffice.")
            self._maybe_restart_unoserver(force_restart=True)
            proc = None
        except subprocess.TimeoutExpired:
            self.logger.error("unoconvert timeout; restarting soffice.")
            self._maybe_restart_unoserver(force_restart=True)
            proc = None
        except ConversionFailedException:
            self._maybe_restart_unoserver(force_restart=True)
            proc = None

        # remove source
        doc_fp.unlink(missing_ok=True)

        if proc is not None and proc.returncode == 0:
            return tgt_fp

        raise ConversionFailedException(
            f"conversion of {doc_fp} to pdf failed"
        )
