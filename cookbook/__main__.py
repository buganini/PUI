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
        parser.add_argument('--session-ttl', type=float, default=900)
        options = vars(parser.parse_args(sys.argv[2:]))
        from .app import Cookbook
        Cookbook().start(**options)
    else:
        from .app import Cookbook
        Cookbook().run()


if __name__ == '__main__':
    main()
