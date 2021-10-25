import json
from pathlib import Path

import click
import rich
import yaml

from . import _core


@click.group()
def cli():
    """kbatch controls batch jobs"""
    pass


@cli.command()
@click.option("--jupyterhub-url")
@click.option("--kbatch-url")
@click.option("--token")
def configure(jupyterhub_url, kbatch_url, token):
    p = _core.configure(jupyterhub_url, kbatch_url, token)
    rich.print(f"[green]Wrote config to[/green] [bold]{str(p)}[/bold]")


@cli.group()
def job():
    pass


@job.command()
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
def list(kbatch_url, token):
    result = _core.list_jobs(kbatch_url, token)
    rich.print(result)


@job.command()
@click.option("--name", help="File to execute.")
@click.option("--description", help="File to execute.")
@click.option("--image", help="File to execute.")
@click.option("--command", help="File to execute.")
@click.option("--args", help="File to execute.")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option("--env", help="File to execute.")
@click.option(
    "-c", "--code", help="Local directory of source-code to make available to the job."
)
@click.option("-f", "--file", help="Configuration file.")
def submit(file, code, name, description, image, command, args, kbatch_url, token, env):
    if command:
        command = json.loads(command)
    if env:
        env = json.loads(env)
    if args:
        args = json.loads(args)

    data = {}
    if file:
        data = yaml.safe_load(Path(file).read_text())
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if image is not None:
        data["image"] = image
    if command is not None:
        data["command"] = command
    if code is not None:
        data["code"] = code

    spec = _core.JobSpec(**data)
    if env:
        spec.env.update(env)

    result = _core.submit_job(
        spec=spec,
        kbatch_url=kbatch_url,
        token=token,
    )
    rich.print(result)
