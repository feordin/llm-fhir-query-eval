import click
from fhir_eval.commands import run, scrape, report, load


@click.group()
@click.version_option()
def cli():
    """FHIR Query Evaluation CLI"""
    pass


cli.add_command(run.run)
cli.add_command(scrape.scrape)
cli.add_command(report.report)
cli.add_command(load.load)


if __name__ == "__main__":
    cli()
