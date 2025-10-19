"""
Modern SSH tunnel implementation using paramiko directly.
This replaces sshtunnel dependency and is compatible with paramiko 4.0+.
"""

import os
import socket
import threading
from typing import Any, Optional, Tuple, cast

import paramiko

from ryutils import log


class ModernSSHTunnel:
    """
    A modern SSH tunnel implementation using paramiko directly.
    Compatible with paramiko 4.0+ and doesn't rely on deprecated DSSKey.
    """

    def __init__(
        self,
        ssh_host: str,
        ssh_port: int,
        ssh_username: str,
        ssh_pkey: str,
        remote_host: str,
        remote_port: int,
        local_port: int = 0,  # 0 means let the system choose
    ):
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.ssh_pkey = ssh_pkey
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_port = local_port

        self.client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
        self.local_socket: Optional[socket.socket] = None
        self.tunnel_thread: Optional[threading.Thread] = None
        self.is_active = False
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the SSH tunnel."""
        try:
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load SSH key
            ssh_key = self._load_ssh_key()

            # Connect to SSH server
            log.print_normal(f"Connecting to SSH server: {self.ssh_host}:{self.ssh_port}")
            self.client.connect(
                hostname=self.ssh_host,
                port=self.ssh_port,
                username=self.ssh_username,
                pkey=ssh_key,
                timeout=30,
            )

            # Get transport for port forwarding
            self.transport = self.client.get_transport()

            # Start local socket server
            self.local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.local_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.local_socket.bind(("127.0.0.1", self.local_port))
            self.local_socket.listen(1)

            # Get the actual local port that was bound
            self.local_port = self.local_socket.getsockname()[1]

            # Start tunnel thread
            self._stop_event.clear()
            self.tunnel_thread = threading.Thread(target=self._tunnel_worker, daemon=True)
            self.tunnel_thread.start()

            self.is_active = True
            log.print_ok_arrow(f"SSH tunnel active: {self.is_active}")
            log.print_normal(
                f"Local port: {self.local_port} -> Remote: {self.remote_host}:{self.remote_port}"
            )

        except Exception as e:  # pylint: disable=broad-except
            log.print_fail(f"Failed to start SSH tunnel: {e}")
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the SSH tunnel."""
        self.is_active = False
        self._stop_event.set()

        if self.tunnel_thread and self.tunnel_thread.is_alive():
            self.tunnel_thread.join(timeout=5)

        if self.local_socket:
            try:
                self.local_socket.close()
            except Exception:  # pylint: disable=broad-except
                pass
            self.local_socket = None

        if self.transport:
            try:
                self.transport.close()
            except Exception:  # pylint: disable=broad-except
                pass
            self.transport = None

        if self.client:
            try:
                self.client.close()
            except Exception:  # pylint: disable=broad-except
                pass
            self.client = None

    def _load_ssh_key(self) -> paramiko.PKey:
        """Load SSH key with compatibility for different key types."""
        try:
            # Try to load the key file
            key_path = os.path.expanduser(self.ssh_pkey)

            # Try different key types in order of preference
            key_types: list[tuple[str, type[paramiko.PKey]]] = [
                ("RSA", paramiko.RSAKey),
                ("Ed25519", paramiko.Ed25519Key),
                ("ECDSA", paramiko.ECDSAKey),
            ]

            # Add DSSKey only if available (for backward compatibility)
            if hasattr(paramiko, "DSSKey"):
                key_types.append(("DSS", paramiko.DSSKey))  # type: ignore

            for key_name, key_class in key_types:
                try:
                    log.print_normal(f"Trying to load {key_name} key from: {key_path}")
                    # Use getattr to access the method dynamically
                    from_private_key_file = getattr(key_class, "from_private_key_file")
                    key = from_private_key_file(key_path)
                    log.print_ok_arrow(f"Successfully loaded {key_name} key")
                    return cast(paramiko.PKey, key)
                except Exception as e:  # pylint: disable=broad-except
                    log.print_normal(f"Failed to load {key_name} key: {e}")
                    continue

            raise ValueError(
                f"Could not load SSH key from {key_path}. Tried: {[kt[0] for kt in key_types]}"
            )

        except Exception as e:  # pylint: disable=broad-except
            log.print_fail(f"Error loading SSH key: {e}")
            raise

    def _tunnel_worker(self) -> None:
        """Worker thread that handles the tunnel connections."""
        while not self._stop_event.is_set():
            try:
                # Accept connection from local client
                if self.local_socket is None:
                    break
                client_socket, _ = self.local_socket.accept()

                # Create a new thread for this connection
                conn_thread = threading.Thread(
                    target=self._handle_connection, args=(client_socket,), daemon=True
                )
                conn_thread.start()

            except socket.error as e:  # pylint: disable=broad-except
                if not self._stop_event.is_set():
                    log.print_fail(f"Socket error in tunnel worker: {e}")
                break
            except Exception as e:  # pylint: disable=broad-except
                if not self._stop_event.is_set():
                    log.print_fail(f"Unexpected error in tunnel worker: {e}")
                break

    def _handle_connection(self, client_socket: socket.socket) -> None:
        """Handle a single tunnel connection."""
        remote_socket = None
        try:
            # Create channel to remote host
            if self.transport is None:
                return
            channel = self.transport.open_channel(
                "direct-tcpip", (self.remote_host, self.remote_port), client_socket.getpeername()
            )

            # Forward data between client and remote
            self._forward_data(client_socket, channel)

        except Exception as e:  # pylint: disable=broad-except
            log.print_fail(f"Error handling tunnel connection: {e}")
        finally:
            try:
                if remote_socket:
                    remote_socket.close()
                client_socket.close()
            except Exception:  # pylint: disable=broad-except
                pass

    def _forward_data(self, client_socket: socket.socket, channel: paramiko.Channel) -> None:
        """Forward data between client socket and SSH channel."""

        def forward(src: Any, dst: Any) -> None:
            try:
                while not self._stop_event.is_set():
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.send(data)
            except Exception:  # pylint: disable=broad-except
                pass

        # Start forwarding threads
        client_to_channel = threading.Thread(
            target=forward, args=(client_socket, channel), daemon=True
        )
        channel_to_client = threading.Thread(
            target=forward, args=(channel, client_socket), daemon=True
        )

        client_to_channel.start()
        channel_to_client.start()

        # Wait for either thread to finish
        client_to_channel.join()
        channel_to_client.join()

        # Clean up
        try:
            channel.close()
        except Exception:  # pylint: disable=broad-except
            pass


# Backward compatibility wrapper
class SSHTunnelForwarder:
    """
    Backward compatibility wrapper for sshtunnel.SSHTunnelForwarder.
    This allows existing code to work without changes.
    """

    def __init__(
        self,
        ssh_address_or_host: Tuple[str, int],
        ssh_username: str,
        ssh_pkey: str,
        remote_bind_address: Tuple[str, int],
        local_bind_address: Tuple[str, int] = ("127.0.0.1", 0),
    ) -> None:
        self.ssh_host, self.ssh_port = ssh_address_or_host
        self.ssh_username = ssh_username
        self.ssh_pkey = ssh_pkey
        self.remote_host, self.remote_port = remote_bind_address
        self.local_host, self.local_port = local_bind_address

        self.tunnel: Optional[ModernSSHTunnel] = None
        self.is_active = False

    def start(self) -> None:
        """Start the SSH tunnel."""
        self.tunnel = ModernSSHTunnel(
            ssh_host=self.ssh_host,
            ssh_port=self.ssh_port,
            ssh_username=self.ssh_username,
            ssh_pkey=self.ssh_pkey,
            remote_host=self.remote_host,
            remote_port=self.remote_port,
            local_port=self.local_port,
        )
        self.tunnel.start()
        self.is_active = self.tunnel.is_active

    def stop(self) -> None:
        """Stop the SSH tunnel."""
        if self.tunnel:
            self.tunnel.stop()
            self.is_active = False

    def __enter__(self) -> "SSHTunnelForwarder":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]
    ) -> None:
        """Context manager exit."""
        self.stop()

    @property
    def local_bind_port(self) -> int:
        """Get the local bind port."""
        if self.tunnel:
            return self.tunnel.local_port
        return self.local_port
