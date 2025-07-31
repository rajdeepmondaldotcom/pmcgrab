"""PMCGrab command-line entry point.

This module serves as the entry point for ``python -m pmcgrab`` command execution.
It provides a thin wrapper that forwards execution to the main CLI functionality
defined in ``pmcgrab.cli.pmcgrab_cli``, allowing the package to be invoked both
as a module and via the ``pmcgrab`` console script declared in ``pyproject.toml``.

Examples:
    Run PMCGrab as a module:

        $ python -m pmcgrab --pmcids 7181753 3539614 --output-dir ./results

    This is equivalent to using the installed console script:

        $ pmcgrab --pmcids 7181753 3539614 --output-dir ./results

Notes:
    This module contains no logic itself - it simply delegates to the main
    CLI implementation to maintain a clean separation of concerns and avoid
    code duplication between module and script execution paths.
"""

from pmcgrab.cli.pmcgrab_cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
