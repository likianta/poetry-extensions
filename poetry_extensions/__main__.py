from argsense import cli

from . import init_template

cli.add_cmd(init_template.main, 'init-template')

if __name__ == '__main__':
    cli.run()
