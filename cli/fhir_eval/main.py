import click
from fhir_eval.commands import run, scrape, report


@click.group()
@click.version_option()
def cli():
    """FHIR Query Evaluation CLI"""
    pass


cli.add_command(run.run)
cli.add_command(scrape.scrape)
cli.add_command(report.report)


if __name__ == "__main__":
    cli()
