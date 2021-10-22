import json

import click
import rich

from . import _core


@click.group()
def cli():
    """kbatch controls batch jobs"""
    pass


@cli.group()
def login():
    pass


@cli.group()
def job():
    pass


@job.command()
@click.option("--url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
def list(url, token):
    result = _core.list(url, token)
    rich.print(result)


@job.command()
@click.option("--name", help="File to execute.")
@click.option("--image", help="File to execute.")
@click.option("--command", help="File to execute.")
@click.option("--file", help="File to execute.")
@click.option("--url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option("--env", help="File to execute.")
def submit(name, image, command, file, url, token, env):
    if command:
        command = json.loads(command)

    if env:
        env = json.loads(env)

    result = _core.submit(name, image, command, file, url, token, env)
    rich.print(result)
