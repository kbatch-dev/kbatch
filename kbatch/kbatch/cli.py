import logging

import click
import rich
import rich.logging
from kubernetes.client.models import V1Job, V1CronJob

from . import _core
from ._types import CronJob, Job


FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[rich.logging.RichHandler()],
)


@click.group()
def cli():
    """kbatch controls batch jobs"""
    pass


@cli.command()
@click.option("--kbatch-url")
@click.option("--token")
def configure(kbatch_url, token):
    """Write a configuration file to use for future kbatch actions."""
    p = _core.configure(kbatch_url, token)
    rich.print(f"[green]Wrote config to[/green] [bold]{str(p)}[/bold]")


@cli.command()
@click.option("--kbatch-url", help="URL to the kbatch server.")
def profiles(kbatch_url):
    """
    Show the profiles used by the server.

    kbatch administrators can serve profiles at the "/profiles" endpoint with
    some configuration values for various profiles.
    """
    p = _core.show_profiles(kbatch_url)
    rich.print_json(data=p)


# CRONJOB
@cli.group()
def cronjob():
    """Manage kbatch cronjobs."""
    pass


@cronjob.command(name="show")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.argument("cronjob_name")
def show_cronjob(cronjob_name, kbatch_url, token):
    """Show the details for a cronjob."""
    result = _core.show_job(cronjob_name, kbatch_url, token, V1CronJob)
    rich.print_json(data=result)


@cronjob.command(name="delete")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.argument("cronjob_name")
def delete_cronjob(cronjob_name, kbatch_url, token):
    """Delete a cronjob, cancelling running jobs and pods."""
    result = _core.delete_job(cronjob_name, kbatch_url, token, V1CronJob)
    rich.print_json(data=result)


@cronjob.command(name="list")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option(
    "-o",
    "--output",
    help="output format",
    type=click.Choice(["json", "table"]),
    default="json",
)
def list_cronjobs(kbatch_url, token, output):
    """List all the cronjobs."""
    results = _core.list_jobs(kbatch_url, token, V1CronJob)

    if output == "json":
        rich.print_json(data=results)
    elif output == "table":
        rich.print(_core.format_cronjobs(results))


@cronjob.command(name="submit")
@click.option("-n", "--name", help="CronJob name.", required=True)
@click.option("--image", help="Container image to use to execute job.")
@click.option("--command", help="Command to execute.")
@click.option("--args", help="Arguments to pass to the command.")
@click.option(
    "--schedule", help="The schedule this cronjob should run on.", required=True
)
@click.option("-e", "--env", help="JSON mapping of environment variables for the job.")
@click.option("-d", "--description", help="A description of the cronjob, optional.")
@click.option(
    "-c",
    "--code",
    help="Local file or directory of source code to make available to the cronjob.",
)
@click.option("-p", "--profile", help="Profile name to use. See 'kbatch profiles'.")
@click.option("-f", "--file", help="Configuration file.")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="JupyterHub API token.")
@click.option(
    "-o",
    "--output",
    default="json",
    help="Output format.",
    type=click.Choice(["json", "name"]),
)
def submit_cronjob(
    file,
    code,
    name,
    description,
    image,
    command,
    args,
    schedule,
    profile,
    kbatch_url,
    token,
    env,
    output,
):
    """
    Submit a CronJob to run on Kubernetes.
    """

    data = _core._prep_job_data(
        file,
        code,
        name,
        description,
        image,
        command,
        args,
        profile,
        kbatch_url,
        env,
    )

    if schedule is not None:
        data["schedule"] = schedule

    cronjob = CronJob(**data)

    result = _core.submit_job(
        job=cronjob,
        kbatch_url=kbatch_url,
        token=token,
        model=V1CronJob,
        code=code,
        profile=profile,
    )
    if output == "json":
        rich.print_json(data=result)
    elif output == "name":
        print(result["metadata"]["name"])


# JOB
@cli.group()
def job():
    """Manage kbatch jobs."""
    pass


@job.command(name="show")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.argument("job_name")
def show_job(job_name, kbatch_url, token):
    """Show the details for a job."""
    result = _core.show_job(job_name, kbatch_url, token, V1Job)
    rich.print_json(data=result)


@job.command(name="delete")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.argument("job_name")
def delete_job(job_name, kbatch_url, token):
    """Delete a job, cancelling running pods."""
    result = _core.delete_job(job_name, kbatch_url, token, V1Job)
    rich.print_json(data=result)


@job.command(name="list")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option(
    "-o",
    "--output",
    help="output format",
    type=click.Choice(["json", "table"]),
    default="json",
)
def list_jobs(kbatch_url, token, output):
    """List all the jobs."""
    results = _core.list_jobs(kbatch_url, token, V1Job)

    if output == "json":
        rich.print_json(data=results)
    elif output == "table":
        rich.print(_core.format_jobs(results))


@job.command(name="submit")
@click.option("-n", "--name", help="Job name.", required=True)
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
@click.option("-p", "--profile", help="Profile name to use. See 'kbatch profiles'.")
@click.option("-f", "--file", help="Configuration file.")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="JupyterHub API token.")
@click.option(
    "-o",
    "--output",
    default="json",
    help="Output format.",
    type=click.Choice(["json", "name"]),
)
def submit_job(
    file,
    code,
    name,
    description,
    image,
    command,
    args,
    profile,
    kbatch_url,
    token,
    env,
    output,
):
    """
    Submit a job to run on Kubernetes.
    """

    data = _core._prep_job_data(
        file,
        code,
        name,
        description,
        image,
        command,
        args,
        profile,
        kbatch_url,
        env,
    )

    job = Job(**data)

    result = _core.submit_job(
        job,
        kbatch_url=kbatch_url,
        token=token,
        model=V1Job,
        code=code,
        profile=profile,
    )
    if output == "json":
        rich.print_json(data=result)
    elif output == "name":
        print(result["metadata"]["name"])


# POD
@cli.group()
def pod():
    """Manage job pods."""
    pass


@pod.command(name="list")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option(
    "--job-name", help="The name of the job to limit the results to.", default=None
)
@click.option(
    "-o",
    "--output",
    help="output format",
    type=click.Choice(["json", "table", "name"]),
    default="json",
)
def list_pods(kbatch_url, token, job_name, output):
    """List all the pods."""
    result = _core.list_pods(kbatch_url, token, job_name)

    if output == "json":
        rich.print_json(data=result)
    elif output == "table":
        rich.print(_core.format_pods(result))
    elif output == "name":
        names = [x["metadata"]["name"] for x in result["items"]]
        rich.print("\n".join(names))


# TODO show pod


@pod.command()
@click.argument("pod_name")
@click.option("--kbatch-url", help="URL to the kbatch server.")
@click.option("--token", help="File to execute.")
@click.option("--stream/--no-stream", help="Whether to stream the logs", default=False)
@click.option("--read-timeout", help="Timeout for reading data", default=60, type=int)
@click.option("--pretty/--no-pretty", default=True)
def logs(pod_name, kbatch_url, token, stream, pretty, read_timeout):
    """Get the logs for a kbatch pod."""
    if pretty:
        print = rich.print

    if stream:
        result = _core.logs_streaming(
            pod_name, kbatch_url, token, read_timeout=read_timeout
        )
    else:
        result = _core.logs(pod_name, kbatch_url, token, read_timeout=read_timeout)

    if stream:
        for line in result:
            print(line)
    else:
        print(result)
