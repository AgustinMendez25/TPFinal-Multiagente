"""Los notebooks se generan desde colab/fuentes y cada celda de código es Python válido."""
import ast
import json

from colab import construir


def _python(fuente: str) -> str:
    """Saca las líneas de shell (!) y las mágicas (%), que no son Python."""
    return "\n".join("" if l.lstrip().startswith(("!", "%")) else l for l in fuente.splitlines())


def test_notebook_arma_celdas():
    nb = construir.notebook([("md", "# Título"), ("code", "x = 1\nprint(x)")])
    assert nb["nbformat"] == 4 and nb["metadata"]["accelerator"] == "GPU"
    assert [c["cell_type"] for c in nb["cells"]] == ["markdown", "code"]
    assert nb["cells"][1]["source"] == ["x = 1\n", "print(x)"]


def test_todos_los_notebooks_generados_son_validos(tmp_path):
    rutas = construir.construir_todos(tmp_path)
    assert rutas, "no hay fuentes en colab/fuentes"
    for ruta in rutas:
        nb = json.loads(ruta.read_text(encoding="utf-8"))
        assert nb["cells"][0]["cell_type"] == "markdown"
        for celda in nb["cells"]:
            if celda["cell_type"] == "code":
                ast.parse(_python("".join(celda["source"])))
