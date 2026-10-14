import argparse


def main():
    from .server import serve
    parser = argparse.ArgumentParser(description='Serve a PUI Web Application class')
    parser.add_argument('factory', help='importable module:Class or module:factory')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--base-url', default='/')
    parser.add_argument('--mount-path', default=None)
    parser.add_argument('--allow-host', dest='allow_hosts', action='append',
                        help='allowed Host name; repeat for multiple hosts (default: *)')
    parser.add_argument('--session-ttl', type=float, default=900)
    parser.add_argument('--max-sessions', type=int, default=64)
    serve(**vars(parser.parse_args()))


if __name__ == '__main__':
    main()
