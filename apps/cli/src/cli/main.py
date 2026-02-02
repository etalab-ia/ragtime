import typer

from cli.commands import gen_template, generate

app = typer.Typer()


@app.command()
def hello(name: str):
    print(f"Hello {name}")


app.add_typer(gen_template.app, name="template")
app.add_typer(generate.app, name="generate")


@app.command()
def version():
    print("rag-facile v0.1.0")


if __name__ == "__main__":
    app()
