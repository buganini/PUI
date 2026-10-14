"""Launch the cookbook with the selected backend's application entry point."""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        import argparse
        parser = argparse.ArgumentParser(description='PUI Web cookbook')
        parser.add_argument('--host', default='localhost')
        parser.add_argument('--port', type=int, default=8866)
        parser.add_argument('--base-url', default='/pui')
        parser.add_argument('--mount-path', default=None)
        parser.add_argument('--allow-host', dest='allow_hosts', action='append',
                            help='allowed Host name; repeat for multiple hosts (default: *)')
        proxies = parser.add_mutually_exclusive_group()
        proxies.add_argument('--trusted-proxy', dest='trusted_proxies', action='append',
                             help='trusted proxy IP/CIDR; repeat to replace defaults (127.0.0.0/8, ::1/128)')
        proxies.add_argument('--no-trusted-proxy', dest='trusted_proxies', action='store_const', const=[],
                             help='ignore forwarded protocol headers from all peers')
        parser.add_argument('--session-ttl', type=float, default=900)
        options = vars(parser.parse_args(sys.argv[2:]))
        from .app import Cookbook
        print(options, flush=True)
        Cookbook().start(**options)
    else:
        from .app import Cookbook
        Cookbook().run()


if __name__ == '__main__':
    main()
