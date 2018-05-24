import pkgutil


def print_config():
    print(pkgutil.get_data('galera_node_health', 'example_files/config.cfg').decode('ascii'))
