"""
Lexicon Workflow
================

This module documents how to work with the **lexicon subsystem** of
_Abstract Wiki Architect_:

- where lexicon files live,
- how they are structured,
- how to build / update them (manually or from Wikidata),
- how to run coverage and sanity checks.

The original long-form documentation can live here as a docstring.
If you want to keep the full Markdown version, paste it inside this
triple-quoted string. Python will happily treat it as a literal.
"""


def main() -> None:
    """
    Minimal CLI entry point.

    For now this just prints the module docstring, so you can do:

        python -m qa_tools.lexicon_coverage_report

    later you can turn this into a real coverage-report script.
    """
    text = __doc__ or ""
    print(text)


if __name__ == "__main__":
    main()
