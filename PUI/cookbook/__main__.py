"""Launch the cookbook with the selected backend's application entry point."""
import sys
import argparse


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        parser = argparse.ArgumentParser(description='PUI Web cookbook')
        parser.add_argument('--passthru', action='store_true', help='run Web application in this process without worker processes')
        parser.add_argument('--bind', default='localhost:8866',
                            help='host:port, [IPv6]:port or Unix socket path (default: localhost:8866)')
        parser.add_argument('--base-url', default='/pui')
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
        parser.add_argument('--codex', action='store_const', const={}, default=None, help='enable Codex with existing CLI login')
        parser.add_argument('--claude', action='store_const', const={}, default=None, help='enable Claude with existing CLI login')
        options = vars(parser.parse_args(sys.argv[2:]))
        options['auth'] = lambda username, password: {'auth': {'test': 'test123', 'dev': 'dev123'}.get(username) == password, 'ai': username == 'dev'}
        options['auth_prompt'] = 'User: test/test123 · Developer (AI): dev/dev123'
        from .app import Cookbook
        print(options, flush=True)
        Cookbook().start(**options)
    else:
        parser = argparse.ArgumentParser(description='PUI native cookbook')
        parser.add_argument('--codex', action='store_const', const={}, default=None, help='enable Codex with existing CLI login')
        parser.add_argument('--claude', action='store_const', const={}, default=None, help='enable Claude with existing CLI login')
        options = vars(parser.parse_args(sys.argv[2:]))
        from .app import Cookbook
        print(options, flush=True)
        Cookbook().run(**options)


if __name__ == '__main__':
    main()
