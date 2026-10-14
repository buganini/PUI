import argparse


def main():
    from . import Application
    parser = argparse.ArgumentParser(description='Serve a PUI Web Application class')
    parser.add_argument('factory', help='importable module:Class or module:factory')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--base-url', default='/')
    parser.add_argument('--mount-path', default=None)
    parser.add_argument('--allow-host', dest='allow_hosts', action='append',
                        help='allowed Host name; repeat for multiple hosts (default: *)')
    proxies = parser.add_mutually_exclusive_group()
    proxies.add_argument('--trusted-proxy', dest='trusted_proxies', action='append',
                         help='trusted proxy IP/CIDR; repeat to replace defaults (127.0.0.0/8, ::1/128)')
    proxies.add_argument('--no-trusted-proxy', dest='trusted_proxies', action='store_const', const=[],
                         help='ignore forwarded protocol headers from all peers')
    parser.add_argument('--session-ttl', type=float, default=900)
    parser.add_argument('--max-sessions', type=int, default=64)
    Application().start(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
