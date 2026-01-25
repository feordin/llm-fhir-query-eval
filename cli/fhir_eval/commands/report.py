import click


@click.command()
@click.option("--format", "-f", type=click.Choice(["json", "markdown", "html"]), default="markdown", help="Report format")
@click.option("--output", "-o", help="Output file path")
def report(format, output):
    """Generate evaluation reports"""
    click.echo(f"Generating {format} report...")
    if output:
        click.echo(f"Output: {output}")

    # TODO: Implement report generation
    click.echo("Not yet implemented")
