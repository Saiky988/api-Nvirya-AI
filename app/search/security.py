import ipaddress
import socket
from urllib.parse import urlparse
from app.core.errors import InvalidRequestError

# Private / reserved IPv4 & IPv6 networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),    # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),   # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local / Cloud metadata (AWS, GCP, Azure)
    ipaddress.ip_network("0.0.0.0/8"),        # Current network
    ipaddress.ip_network("100.64.0.0/10"),    # Carrier-grade NAT
    ipaddress.ip_network("198.18.0.0/15"),    # Benchmark testing
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),         # IPv6 unique local
    ipaddress.ip_network("::ffff:0:0/96"),    # IPv4-mapped IPv6
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}

def is_ip_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks if an IP address is public and safe to connect to."""
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
        return False
    for net in BLOCKED_NETWORKS:
        if ip in net:
            return False
    return True

def validate_url_security(url: str) -> str:
    """
    Validates URL scheme and resolves IP to prevent SSRF.
    Raises InvalidRequestError if URL points to localhost or private network.
    """
    if not url or not isinstance(url, str):
        raise InvalidRequestError("Invalid URL provided.")

    parsed = urlparse(url.strip())
    
    # 1. Check scheme
    if parsed.scheme.lower() not in ("http", "https"):
        raise InvalidRequestError(f"Unsupported protocol: '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise InvalidRequestError("URL must contain a valid hostname.")

    hostname_clean = hostname.strip().lower()

    # 2. Check blocked hostnames
    if hostname_clean in BLOCKED_HOSTNAMES or hostname_clean.endswith(".local") or hostname_clean.endswith(".internal"):
        raise InvalidRequestError(f"Access to host '{hostname}' is blocked for security.")

    # 3. Check if hostname is direct IP
    try:
        ip = ipaddress.ip_address(hostname_clean)
        if not is_ip_allowed(ip):
            raise InvalidRequestError(f"Access to private IP address '{hostname}' is blocked.")
        return url
    except ValueError:
        # Not a raw IP literal, resolve hostname via DNS
        pass

    # 4. DNS resolution to check resolved IPs
    try:
        resolved_ips = socket.getaddrinfo(hostname_clean, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in resolved_ips:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if not is_ip_allowed(ip_obj):
                raise InvalidRequestError(f"Destination hostname '{hostname}' resolves to private address '{ip_str}' and is blocked.")
    except socket.gaierror:
        raise InvalidRequestError(f"Could not resolve hostname '{hostname}'.")

    return url
