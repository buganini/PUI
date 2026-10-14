"""Keep the Web gateway free of cookbook State/application imports."""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        import argparse
        from PUI.web.server import serve
        parser = argparse.ArgumentParser(description='PUI Web cookbook')
        parser.add_argument('--host', default='localhost')
        parser.add_argument('--port', type=int, default=8866)
        parser.add_argument('--base-url', default='/pui')
        parser.add_argument('--mount-path', default=None)
        parser.add_argument('--session-ttl', type=float, default=900)
        serve('cookbook.app:Cookbook', **vars(parser.parse_args(sys.argv[2:])))
    else:
        from .app import Cookbook
        Cookbook().run()


if __name__ == '__main__':
    main()
