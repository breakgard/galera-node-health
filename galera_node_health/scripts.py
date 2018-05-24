#!/usr/bin/python3


def main(*test_args):                              # runs as standalone on gevent server, main launch script
    from gevent.pywsgi import WSGIServer
    from galera_node_health import GaleraNodeHealth, examples
    import argparse
    import configparser
    import sys
    import traceback

    arg_parser = argparse.ArgumentParser(description='Launch galera-node-health using gevent server')
    arg_parser.add_argument('-v', dest='print_config', action='store_true', default=False,
                            help="Print config read during startup")
    arg_parser.add_argument('--print-example-config', dest='example_config', action='store_true', default=False,
                            help="Print example config and exit")
    arg_parser.add_argument('-f', dest='config_file', help="Path to file containing config")
    arg_parser.add_argument('--docker-logs-fix', dest="docker_logs_fix", action="store_true", default=False,
                            help=argparse.SUPPRESS)
    if not test_args:
        args_parsed = arg_parser.parse_args()
    else:
        args_parsed = arg_parser.parse_args(test_args)

    # Fix for `docker logs` command - turn line buffering and redirect to stdout and stderr
    if args_parsed.docker_logs_fix:
        sys.stdout = open('/dev/stdout', 'w', 1)
        sys.stderr = open('/dev/stderr', 'w', 1)

    if args_parsed.example_config:
        examples.print_config()
        if not test_args:
            sys.exit(0)
        else:
            return 'Printed'

    if args_parsed.config_file:
        config = configparser.ConfigParser(inline_comment_prefixes="#")
        try:
            with open(args_parsed.config_file, 'r') as f:
                config.read_file(f)
                checker_port = int(config.get('checker', 'port', fallback=8080))
                checker_address = config.get('checker', 'address', fallback='0.0.0.0')
            galera_health = GaleraNodeHealth(config_file=args_parsed.config_file, print_config=args_parsed.print_config)
        except Exception:
            traceback.print_exc()
            print("Cannot find or access config file: " + str(args_parsed.config_file))
            print("Please make sure it exists and has proper permissions")
            sys.exit(1)
    else:
        checker_port = 8080
        checker_address = '0.0.0.0'
        galera_health = GaleraNodeHealth(print_config=args_parsed.print_config)

    http_server = WSGIServer((checker_address, checker_port), galera_health.flask_app)
    try:
        http_server.serve_forever()
    except OSError as e:
        if e.errno == 98:
            print("Cannot start server - address already in use: " + checker_address + ":" + str(checker_port))
            print("Make sure nothing is running on that address/port or change address/port in config")
            sys.exit(1)
        else:
            raise
    except KeyboardInterrupt:
        print("Shutting down server because of keyboard interrupt")
    finally:
        if not http_server.closed:
            http_server.close()


def dev():
    from galera_node_health import GaleraNodeHealth

    print("---Running checker as standalone flask app - not recommended for production!---")
    galera_health = GaleraNodeHealth()
    galera_health.run()


#def create_fcgi():
#    print("---Printing example .fcgi script---")
#    print("""---------------------------------------------------
##!/usr/bin/python3
#
#from flup.server.fcgi import WSGIServer
#from galera_node_health import GaleraNodeHealth
#
#
#if __name__ == '__main__':
#    galera_node_health = GaleraNodeHealth(config_file=None, root_fix=False)
#    WSGIServer(galera_node_health.flask_app).run()
#---------------------------------------------------""")
#    print("Tips:")
#    print("config_file - change None for path to config file (you can run galera-node-health --print-example-config)")
#    print("root_fix - change to True if deploying to root of the FastCGI server")
#    print()
#    print("It is recommended that the FastCGI server runs the script using a python virtual environment")
#    print("When setting up the virtual environment using pip, the required packages are:")
#    print("galera-node-health flask pymysql flup")