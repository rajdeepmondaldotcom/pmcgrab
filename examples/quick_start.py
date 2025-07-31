#!/usr/bin/env python3
"""
Quick Start Example for pmcgrab

This example demonstrates how to use pmcgrab to fetch and process
a PubMed Central article.

Run with: uv run python examples/quick_start.py
"""

from pmcgrab import Paper


def main():
    """Demonstrate basic usage of pmcgrab."""
    print("pmcgrab Quick Start Example")
    print("=" * 40)

    # Example PMC ID
    pmc_id = "7181753"
    email = "your.email@example.com"  # Required by NCBI API

    print(f"Fetching PMC article: {pmc_id}")

    try:
        # Fetch and parse the paper
        paper = Paper.from_pmc(pmc_id, email)

        # Display basic information
        print(f"Title: {paper.title}")
        print(f"Journal: {paper.journal_title}")
        print(
            f"Published: {paper.published_date.get('epub', 'N/A') if paper.published_date else 'N/A'}"
        )
        print(f"Authors: {len(paper.authors) if paper.authors is not None else 0}")
        print(
            f"Abstract length: {len(paper.abstract) if paper.abstract is not None else 0} characters"
        )

        # Show available sections - body is a list of TextSection objects
        if paper.body is not None and len(paper.body) > 0:
            print(f"Body sections: {len(paper.body)} sections found")

            # Try to show section titles if available
            section_titles = []
            for i, section in enumerate(paper.body):
                if hasattr(section, "title") and section.title:
                    section_titles.append(section.title)
                else:
                    section_titles.append(f"Section {i + 1}")

            print(f"Section titles: {section_titles}")

            # Show a snippet from the first section
            if len(paper.body) > 0:
                first_section = paper.body[0]
                section_text = str(first_section)
                print("\nFirst section snippet:")
                print("-" * 30)
                print(
                    section_text[:300] + "..."
                    if len(section_text) > 300
                    else section_text
                )
        else:
            print("No body content available")

        print("\nSuccess! Paper processed successfully.")

    except Exception as e:
        print(f"Error processing paper: {e}")
        print("Make sure you have internet access and the PMC ID is valid.")


if __name__ == "__main__":
    main()
