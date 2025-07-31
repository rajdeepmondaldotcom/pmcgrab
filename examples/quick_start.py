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
    print("🧬 pmcgrab Quick Start Example")
    print("=" * 40)
    
    # Example PMC ID
    pmc_id = "7181753"
    email = "your.email@example.com"  # Required by NCBI API
    
    print(f"📥 Fetching PMC article: {pmc_id}")
    
    try:
        # Fetch and parse the paper
        paper = Paper.from_pmc(pmc_id, email)
        
        # Display basic information
        print(f"📄 Title: {paper.title}")
        print(f"📰 Journal: {paper.journal_title}")
        print(f"📅 Published: {paper.published_date.get('epub', 'N/A')}")
        print(f"👥 Authors: {len(paper.authors) if paper.authors else 0}")
        print(f"📝 Abstract length: {len(paper.abstract) if paper.abstract else 0} characters")
        
        # Show available sections
        if paper.body:
            print(f"📚 Available sections: {list(paper.body.keys())}")
            
            # Show a snippet from the introduction
            if "Introduction" in paper.body:
                intro_text = paper.body["Introduction"]
                print(f"\n📖 Introduction snippet:")
                print("-" * 30)
                print(intro_text[:300] + "..." if len(intro_text) > 300 else intro_text)
        
        print("\n✅ Success! Paper processed successfully.")
        
    except Exception as e:
        print(f"❌ Error processing paper: {e}")
        print("💡 Make sure you have internet access and the PMC ID is valid.")


if __name__ == "__main__":
    main()