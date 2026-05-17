"""Command-line interface for PMCGrab article processing.

The CLI is implemented in :mod:`pmcgrab.cli.pmcgrab_cli` and is exposed through
both the ``pmcgrab`` console script and ``python -m pmcgrab``.

Supported input modes are mutually exclusive:

* ``--pmcids`` for PMC IDs
* ``--pmids`` for PubMed IDs, converted to PMC IDs through NCBI
* ``--dois`` for DOI inputs, converted to PMC IDs through NCBI
* ``--from-id-file`` for one ID per line
* ``--from-dir`` for a directory of local JATS XML files
* ``--from-file`` for specific local JATS XML files

Common examples:

.. code-block:: bash

    pmcgrab --pmcids 7181753 3539614 --output-dir ./results
    pmcgrab --from-id-file ids.txt --format jsonl --output-dir ./results
    pmcgrab --from-dir ./pmc_bulk_xml --workers 16 --output-dir ./results
    python -m pmcgrab --version

The CLI writes normalized JSON by default. With ``--format jsonl``, it writes a
single newline-delimited JSON file in the output directory.
"""
