import argparse


def main():
    from . import Application
    parser = argparse.ArgumentParser(description='Serve a PUI Web Application class')
    parser.add_argument('factory', help='importable module:Class or module:factory')
    parser.add_argument('--passthru', action='store_true', help='run one retained application in this process, without worker processes')
    parser.add_argument('--permissive-takeover', action='store_true', help='allow another browser/account to take over the retained session (requires --passthru)')
    parser.add_argument('--title', default='', help='application/page title (default: use the worker app or Window title)')
    parser.add_argument('--bind', default='127.0.0.1:8000',
                        help='host:port, [IPv6]:port or Unix socket path (default: 127.0.0.1:8000)')
    parser.add_argument('--mount-path', default=None)
    parser.add_argument('--allow-host', dest='allow_hosts', action='append',
                        help='allowed Host name; repeat for multiple hosts (default: *)')
    proxies = parser.add_mutually_exclusive_group()
    proxies.add_argument('--trusted-proxy', dest='trusted_proxies', action='append',
                         help='trusted proxy IP/CIDR or unix; repeat to replace defaults (127.0.0.0/8, ::1/128, unix)')
    proxies.add_argument('--no-trusted-proxy', dest='trusted_proxies', action='store_const', const=[],
                         help='ignore forwarded protocol headers from all peers')
    parser.add_argument('--session-ttl', type=float, default=900,
                        help='disconnected session lifetime in seconds; 0 never expires (default: 900)')
    parser.add_argument('--max-sessions', type=int, default=64)
    options = vars(parser.parse_args())
    Application(title=options.pop('title')).start(**options)


if __name__ == '__main__':
    main()
