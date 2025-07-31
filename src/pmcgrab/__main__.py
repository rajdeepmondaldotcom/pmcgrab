"""Entrypoint for ``python -m pmcgrab``.

This thin wrapper simply forwards execution to the public CLI defined in
``pmcgrab.cli.pmcgrab_cli`` so that the package can be invoked both as a
module and via the ``pmcgrab`` console script that is declared in
``pyproject.toml``.
"""

from pmcgrab.cli.pmcgrab_cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
