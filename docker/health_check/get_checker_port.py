#!/usr/bin/python3

if __name__ == '__main__':
    from configparser import ConfigParser
    import sys

    c = ConfigParser()
    c.read(sys.argv[1])
    print(str(c.get('checker', 'port', fallback=8080)))
    sys.exit(0)