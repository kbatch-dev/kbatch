import json
from pathlib import Path

import click
import rich
import yaml

from . import _core
from ._types import Job


@click.group()
def cli():
    """kbatch controls batch jobs"""
    pass


@cli.command()
@click.option("--kbatch-url")
@click.option("--token")
def configure(kbatch_url, token):
    p = _core.configure(kbatch_url, token)
    rich.print(f"[green]Wrote config to[/green] [bold]{str(p)}[/bold]")


@cli.group()
def job():
    pass


@job.command()
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.argument("job_name")
def show(job_name, kbatch_url, token):
    result = _core.show_job(job_name, kbatch_url, token)
    rich.print_json(data=result)


@job.command()
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option(
    "-o",
    "--output",
    help="output format",
    type=click.Choice(["json", "table"]),
    default="json",
)
def list(kbatch_url, token, output):
    result = _core.list_jobs(kbatch_url, token)

    if output == "json":
        rich.print_json(data=result)
    elif output == "table":
        rich.print(_core.format_jobs(result))


@job.command()
@click.option("-n", "--name", help="Job name.")
@click.option("--image", help="Container image to use to execute job.")
@click.option("--command", help="Command to execute.")
@click.option("--args", help="Arguments to pass to the command.")
@click.option("-e", "--env", help="JSON mapping of environment variables for the job.")
@click.option("-d", "--description", help="A description of the job, optional.")
@click.option(
    "-c",
    "--code",
    help="Local file or directory of source code to make available to the job.",
)
@click.option("-f", "--file", help="Configuration file.")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="JupyterHub API token.")
def submit(file, code, name, description, image, command, args, kbatch_url, token, env):
    """
    Submit a job to run on Kubernetes.
    """
    if command:
        command = json.loads(command)
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
    if args is not None:
        data["args"] = args
    if command is not None:
        data["command"] = command
    if env:
        env = json.loads(env)
        data["env"] = env

    code = code or data.pop("code", None)

    job = Job(**data)

    result = _core.submit_job(
        job,
        code=code,
        kbatch_url=kbatch_url,
        token=token,
    )
    rich.print_json(data=result)


@job.command()
@click.argument("job_name")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option("--pretty/--no-pretty", default=True)
def logs(job_name, kbatch_url, token, pretty):
    result = _core.logs(job_name, kbatch_url, token)
    if pretty:
        import rich

        rich.print(result)
    else:
        print(result)
