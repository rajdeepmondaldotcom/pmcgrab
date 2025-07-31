# Advanced Usage

Advanced patterns and techniques for power users of PMCGrab.

## Custom Processing Pipelines

### Building a Research Data Pipeline

```python
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any
import json
import pandas as pd
from pmcgrab import Paper, process_pmc_ids_in_batches

class ResearchPipeline:
    """Advanced research data processing pipeline."""

    def __init__(self, email: str, output_dir: str = "./pipeline_output"):
        self.email = email
        self.output_dir = Path(output_dir)
        self.setup_logging()

    def setup_logging(self):
        """Configure comprehensive logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'pipeline.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def process_systematic_review(self,
                                 pmc_ids: List[str],
                                 research_domain: str) -> Dict[str, Any]:
        """Process papers for systematic review with domain-specific analysis."""

        self.logger.info(f"Starting systematic review for {research_domain}")
        domain_dir = self.output_dir / research_domain
        domain_dir.mkdir(parents=True, exist_ok=True)

        # Process papers with optimized settings
        process_pmc_ids_in_batches(
            pmc_ids=pmc_ids,
            output_dir=str(domain_dir / "raw_papers"),
            batch_size=30,
            max_workers=12,
            max_retries=5,
            timeout=90,
            email=self.email,
            verbose=True
        )

        # Post-process and analyze
        papers = self.load_papers(domain_dir / "raw_papers")
        analysis = self.analyze_research_domain(papers, research_domain)

        # Generate reports
        self.generate_systematic_review_report(analysis, domain_dir)

        return analysis

    def load_papers(self, papers_dir: Path) -> List[Dict[str, Any]]:
        """Load and validate processed papers."""
        papers = []
        for json_file in papers_dir.glob("PMC*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    paper = json.load(f)
                papers.append(paper)
            except Exception as e:
                self.logger.error(f"Failed to load {json_file}: {e}")

        self.logger.info(f"Loaded {len(papers)} papers successfully")
        return papers

    def analyze_research_domain(self, papers: List[Dict], domain: str) -> Dict[str, Any]:
        """Perform domain-specific analysis."""
        analysis = {
            'domain': domain,
            'total_papers': len(papers),
            'date_range': self.get_date_range(papers),
            'journal_distribution': self.get_journal_distribution(papers),
            'methodology_analysis': self.analyze_methodologies(papers),
            'keyword_analysis': self.analyze_keywords(papers),
            'citation_network': self.build_citation_network(papers)
        }

        return analysis

# Usage example
pipeline = ResearchPipeline(email="researcher@university.edu")
covid_papers = ["7181753", "8378853", "7462677"]  # Example PMC IDs
analysis = pipeline.process_systematic_review(covid_papers, "covid19_therapeutics")
```

### Parallel Processing with Custom Error Handling

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time
from typing import List, Tuple, Optional
from pmcgrab import Paper

class AdvancedProcessor:
    """Advanced parallel processor with custom error handling and rate limiting."""

    def __init__(self, email: str, max_concurrent: int = 10, rate_limit: float = 0.5):
        self.email = email
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit  # seconds between requests
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.last_request_time = 0

    async def process_with_rate_limiting(self, pmcid: str) -> Tuple[str, Optional[Paper], Optional[str]]:
        """Process single paper with rate limiting and error handling."""
        async with self.semaphore:
            # Rate limiting
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed)

            self.last_request_time = time.time()

            try:
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                paper = await loop.run_in_executor(
                    None,
                    lambda: Paper.from_pmc(pmcid, email=self.email, timeout=60)
                )
                return pmcid, paper, None

            except Exception as e:
                return pmcid, None, str(e)

    async def process_batch_async(self, pmc_ids: List[str]) -> Dict[str, Any]:
        """Process batch of papers asynchronously with advanced error handling."""
        tasks = [self.process_with_rate_limiting(pmcid) for pmcid in pmc_ids]

        results = {
            'successful': [],
            'failed': [],
            'processing_time': 0
        }

        start_time = time.time()

        # Process with progress tracking
        completed = 0
        for coro in asyncio.as_completed(tasks):
            pmcid, paper, error = await coro
            completed += 1

            if paper:
                results['successful'].append({
                    'pmcid': pmcid,
                    'paper': paper,
                    'processing_order': completed
                })
                print(f"✓ Processed PMC{pmcid} ({completed}/{len(pmc_ids)})")
            else:
                results['failed'].append({
                    'pmcid': pmcid,
                    'error': error,
                    'processing_order': completed
                })
                print(f"✗ Failed PMC{pmcid}: {error}")

        results['processing_time'] = time.time() - start_time
        return results

# Usage
async def main():
    processor = AdvancedProcessor(
        email="researcher@university.edu",
        max_concurrent=8,
        rate_limit=0.3
    )

    pmc_ids = ["7181753", "3539614", "5454911", "8378853"]
    results = await processor.process_batch_async(pmc_ids)

    print(f"Successful: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Total time: {results['processing_time']:.2f}s")

# Run the async processing
asyncio.run(main())
```

## Advanced Content Analysis

### Multi-Modal Content Extraction

```python
from pmcgrab import Paper
import pandas as pd
import re
from collections import defaultdict, Counter
from typing import Dict, List, Any
import networkx as nx
import matplotlib.pyplot as plt

class ContentAnalyzer:
    """Advanced content analysis for research papers."""

    def __init__(self):
        self.methodology_patterns = {
            'machine_learning': [
                r'\b(machine learning|deep learning|neural network|random forest|svm|support vector)\b',
                r'\b(classification|regression|clustering|supervised|unsupervised)\b'
            ],
            'statistical_analysis': [
                r'\b(t-test|anova|chi-square|regression analysis|p-value)\b',
                r'\b(statistical significance|confidence interval|standard deviation)\b'
            ],
            'experimental_design': [
                r'\b(randomized|controlled trial|double-blind|placebo)\b',
                r'\b(sample size|power analysis|inclusion criteria)\b'
            ]
        }

    def extract_methodologies(self, papers: List[Dict]) -> Dict[str, Dict]:
        """Extract and categorize methodologies from papers."""
        methodology_analysis = defaultdict(lambda: defaultdict(list))

        for paper in papers:
            methods_text = paper.get('Body', {}).get('Methods', '')
            if not methods_text:
                continue

            methods_lower = methods_text.lower()

            for category, patterns in self.methodology_patterns.items():
                matches = []
                for pattern in patterns:
                    matches.extend(re.findall(pattern, methods_lower, re.IGNORECASE))

                if matches:
                    methodology_analysis[category]['papers'].append(paper['PMCID'])
                    methodology_analysis[category]['methods'].extend(matches)

        # Summarize findings
        summary = {}
        for category, data in methodology_analysis.items():
            summary[category] = {
                'paper_count': len(data['papers']),
                'unique_methods': len(set(data['methods'])),
                'most_common': Counter(data['methods']).most_common(5)
            }

        return summary

    def build_citation_network(self, papers: List[Dict]) -> nx.DiGraph:
        """Build citation network from papers."""
        G = nx.DiGraph()

        # Add nodes for all papers
        for paper in papers:
            G.add_node(paper['PMCID'],
                      title=paper['Title'][:50] + '...',
                      journal=paper.get('Journal', 'Unknown'))

        # Add citation edges
        for paper in papers:
            citing_paper = paper['PMCID']
            citations = paper.get('Citations', [])

            for citation in citations:
                # Try to match citations to papers in our dataset
                cited_pmcid = self.extract_pmcid_from_citation(citation)
                if cited_pmcid and cited_pmcid in G.nodes():
                    G.add_edge(citing_paper, cited_pmcid)

        return G

    def extract_pmcid_from_citation(self, citation: Dict) -> str:
        """Extract PMCID from citation if available."""
        # This is a simplified example - real implementation would be more robust
        pmid = citation.get('PMID')
        if pmid:
            # In practice, you'd use ID conversion services
            return f"PMC{pmid}"  # Simplified mapping
        return None

    def analyze_temporal_trends(self, papers: List[Dict]) -> Dict[str, Any]:
        """Analyze temporal trends in the research."""
        df = pd.DataFrame([
            {
                'pmcid': p['PMCID'],
                'title': p['Title'],
                'pub_date': pd.to_datetime(p.get('PubDate', ''), errors='coerce'),
                'journal': p.get('Journal', 'Unknown'),
                'num_citations': len(p.get('Citations', [])),
                'has_methods': bool(p.get('Body', {}).get('Methods', ''))
            }
            for p in papers
        ])

        df = df.dropna(subset=['pub_date'])
        df['year'] = df['pub_date'].dt.year
        df['month'] = df['pub_date'].dt.month

        trends = {
            'yearly_distribution': df.groupby('year').size().to_dict(),
            'journal_trends': df.groupby(['year', 'journal']).size().unstack(fill_value=0),
            'methods_adoption': df.groupby(['year', 'has_methods']).size().unstack(fill_value=0),
            'citation_trends': df.groupby('year')['num_citations'].agg(['mean', 'median', 'std']).round(2)
        }

        return trends

    def generate_research_insights(self, papers: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive research insights."""
        insights = {
            'dataset_summary': {
                'total_papers': len(papers),
                'unique_journals': len(set(p.get('Journal', 'Unknown') for p in papers)),
                'date_range': self.get_date_range(papers),
                'avg_citations_per_paper': sum(len(p.get('Citations', [])) for p in papers) / len(papers)
            },
            'methodologies': self.extract_methodologies(papers),
            'temporal_trends': self.analyze_temporal_trends(papers),
            'collaboration_network': self.analyze_collaborations(papers),
            'content_metrics': self.analyze_content_metrics(papers)
        }

        return insights

# Usage example
analyzer = ContentAnalyzer()

# Load papers
papers = []
for pmcid in ["7181753", "3539614", "5454911"]:
    try:
        paper = Paper.from_pmc(pmcid, email="researcher@university.edu")
        papers.append(paper.to_dict())
    except Exception as e:
        print(f"Failed to load PMC{pmcid}: {e}")

# Generate insights
insights = analyzer.generate_research_insights(papers)
print(f"Analysis complete for {insights['dataset_summary']['total_papers']} papers")
```

## Custom Data Transformation

### Preparing Data for Machine Learning

```python
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import re
from typing import List, Dict, Tuple

class MLDataPreparator:
    """Prepare PMCGrab data for machine learning applications."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )
        self.label_encoder = LabelEncoder()

    def prepare_classification_dataset(self,
                                     papers: List[Dict],
                                     target_field: str = 'Journal') -> Tuple[pd.DataFrame, np.ndarray]:
        """Prepare dataset for research domain classification."""

        # Extract features
        features = []
        labels = []

        for paper in papers:
            # Combine text features
            text_features = self.extract_text_features(paper)
            numerical_features = self.extract_numerical_features(paper)
            metadata_features = self.extract_metadata_features(paper)

            combined_features = {
                **text_features,
                **numerical_features,
                **metadata_features,
                'pmcid': paper['PMCID']
            }

            features.append(combined_features)
            labels.append(paper.get(target_field, 'Unknown'))

        # Create DataFrame
        df = pd.DataFrame(features)

        # Encode target labels
        y = self.label_encoder.fit_transform(labels)

        return df, y

    def extract_text_features(self, paper: Dict) -> Dict[str, Any]:
        """Extract text-based features from paper."""
        # Combine relevant text sections
        text_sections = []

        # Abstract
        if paper.get('Abstract'):
            abstract_text = ' '.join(paper['Abstract'].values())
            text_sections.append(abstract_text)

        # Key body sections
        body = paper.get('Body', {})
        for section in ['Introduction', 'Methods', 'Results', 'Discussion']:
            if section in body:
                text_sections.append(body[section][:1000])  # Limit length

        combined_text = ' '.join(text_sections)

        # Extract features
        features = {
            'text_length': len(combined_text),
            'word_count': len(combined_text.split()),
            'sentence_count': len(re.split(r'[.!?]+', combined_text)),
            'avg_word_length': np.mean([len(word) for word in combined_text.split()]) if combined_text else 0,
            'technical_term_density': self.calculate_technical_density(combined_text),
            'methodology_keywords': self.count_methodology_keywords(combined_text)
        }

        return features

    def extract_numerical_features(self, paper: Dict) -> Dict[str, float]:
        """Extract numerical features from paper."""
        return {
            'author_count': len(paper.get('Authors', [])),
            'citation_count': len(paper.get('Citations', [])),
            'table_count': len(paper.get('Tables', [])),
            'figure_count': len(paper.get('Figures', [])),
            'section_count': len(paper.get('Body', {})),
            'abstract_section_count': len(paper.get('Abstract', {}))
        }

    def extract_metadata_features(self, paper: Dict) -> Dict[str, Any]:
        """Extract metadata features."""
        pub_date = pd.to_datetime(paper.get('PubDate', ''), errors='coerce')

        features = {
            'publication_year': pub_date.year if pd.notna(pub_date) else 2020,
            'has_doi': bool(paper.get('DOI')),
            'has_keywords': bool(paper.get('Keywords')),
            'has_mesh_terms': bool(paper.get('MeshTerms')),
            'has_funding': bool(paper.get('Funding'))
        }

        return features

    def calculate_technical_density(self, text: str) -> float:
        """Calculate density of technical terms in text."""
        technical_patterns = [
            r'\b\w+ly\b',  # Adverbs ending in -ly
            r'\b\w+tion\b',  # Words ending in -tion
            r'\b\w+ment\b',  # Words ending in -ment
            r'\bp[-<]?\s*0\.\d+\b',  # P-values
            r'\b\d+\.\d+\s*±\s*\d+\.\d+\b',  # Mean ± SD
            r'\b[A-Z]{2,}\b'  # Acronyms
        ]

        total_matches = 0
        for pattern in technical_patterns:
            total_matches += len(re.findall(pattern, text, re.IGNORECASE))

        word_count = len(text.split())
        return total_matches / word_count if word_count > 0 else 0

    def count_methodology_keywords(self, text: str) -> int:
        """Count methodology-related keywords."""
        methodology_keywords = [
            'analysis', 'method', 'approach', 'technique', 'algorithm',
            'model', 'framework', 'protocol', 'procedure', 'assay'
        ]

        text_lower = text.lower()
        return sum(text_lower.count(keyword) for keyword in methodology_keywords)

    def create_tfidf_features(self, papers: List[Dict], max_features: int = 1000) -> np.ndarray:
        """Create TF-IDF feature matrix from paper abstracts."""
        # Extract abstracts
        abstracts = []
        for paper in papers:
            abstract_text = ' '.join(paper.get('Abstract', {}).values())
            abstracts.append(abstract_text if abstract_text else 'No abstract available')

        # Create TF-IDF matrix
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )

        tfidf_matrix = self.vectorizer.fit_transform(abstracts)
        return tfidf_matrix.toarray()

# Usage example
preparator = MLDataPreparator()

# Load papers for different research domains
ml_papers = []  # Papers about machine learning
bio_papers = []  # Papers about biology
med_papers = []  # Papers about medicine

# Combine and prepare dataset
all_papers = ml_papers + bio_papers + med_papers
df, labels = preparator.prepare_classification_dataset(all_papers, target_field='research_domain')

# Create TF-IDF features
tfidf_features = preparator.create_tfidf_features(all_papers)

# Split for training
X_train, X_test, y_train, y_test = train_test_split(
    tfidf_features, labels, test_size=0.2, random_state=42, stratify=labels
)

print(f"Training set: {X_train.shape}")
print(f"Test set: {X_test.shape}")
print(f"Feature names: {preparator.vectorizer.get_feature_names_out()[:10]}")
```

## Integration with External Services

### Building a Research Knowledge Graph

```python
import json
import requests
from typing import Dict, List, Set
import networkx as nx
from pmcgrab import Paper
import time

class ResearchKnowledgeGraph:
    """Build a knowledge graph from PMC papers with external service integration."""

    def __init__(self, email: str):
        self.email = email
        self.graph = nx.MultiDiGraph()
        self.entity_cache = {}
        self.api_delay = 0.5  # Rate limiting

    def build_graph_from_papers(self, pmc_ids: List[str]) -> nx.MultiDiGraph:
        """Build comprehensive knowledge graph from papers."""

        for pmcid in pmc_ids:
            try:
                print(f"Processing PMC{pmcid}...")
                paper = Paper.from_pmc(pmcid, email=self.email)
                self.add_paper_to_graph(paper)
                time.sleep(self.api_delay)  # Rate limiting

            except Exception as e:
                print(f"Failed to process PMC{pmcid}: {e}")

        return self.graph

    def add_paper_to_graph(self, paper: Paper):
        """Add paper and its relationships to the knowledge graph."""
        paper_dict = paper.to_dict()
        pmcid = paper_dict['PMCID']

        # Add paper node
        self.graph.add_node(
            pmcid,
            type='paper',
            title=paper_dict['Title'],
            journal=paper_dict.get('Journal'),
            pub_date=paper_dict.get('PubDate'),
            doi=paper_dict.get('DOI')
        )

        # Add author nodes and relationships
        self.add_authors_to_graph(pmcid, paper_dict.get('Authors', []))

        # Add journal node and relationship
        if paper_dict.get('Journal'):
            self.add_journal_to_graph(pmcid, paper_dict['Journal'])

        # Add keyword nodes and relationships
        self.add_keywords_to_graph(pmcid, paper_dict.get('Keywords', []))

        # Add MeSH term nodes and relationships
        self.add_mesh_terms_to_graph(pmcid, paper_dict.get('MeshTerms', []))

        # Add citation relationships
        self.add_citations_to_graph(pmcid, paper_dict.get('Citations', []))

        # Extract and add entities from text
        self.extract_entities_from_text(pmcid, paper_dict)

    def add_authors_to_graph(self, pmcid: str, authors: List[Dict]):
        """Add author nodes and authorship relationships."""
        for i, author in enumerate(authors):
            author_name = f"{author.get('FirstName', '')} {author.get('LastName', '')}".strip()
            if not author_name:
                continue

            author_id = f"author_{author_name.replace(' ', '_').lower()}"

            # Add author node
            self.graph.add_node(
                author_id,
                type='author',
                name=author_name,
                affiliation=author.get('Affiliation'),
                orcid=author.get('ORCID')
            )

            # Add authorship relationship
            self.graph.add_edge(
                author_id, pmcid,
                type='authored',
                position=i + 1
            )

    def add_journal_to_graph(self, pmcid: str, journal_name: str):
        """Add journal node and publication relationship."""
        journal_id = f"journal_{journal_name.replace(' ', '_').lower()}"

        # Add journal node
        self.graph.add_node(
            journal_id,
            type='journal',
            name=journal_name
        )

        # Add publication relationship
        self.graph.add_edge(
            pmcid, journal_id,
            type='published_in'
        )

    def add_keywords_to_graph(self, pmcid: str, keywords: List[str]):
        """Add keyword nodes and relationships."""
        for keyword in keywords:
            keyword_id = f"keyword_{keyword.replace(' ', '_').lower()}"

            # Add keyword node
            self.graph.add_node(
                keyword_id,
                type='keyword',
                term=keyword
            )

            # Add relationship
            self.graph.add_edge(
                pmcid, keyword_id,
                type='has_keyword'
            )

    def add_mesh_terms_to_graph(self, pmcid: str, mesh_terms: List[Dict]):
        """Add MeSH term nodes and relationships."""
        for mesh_term in mesh_terms:
            if isinstance(mesh_term, str):
                term = mesh_term
                major_topic = False
            else:
                term = mesh_term.get('Term', '')
                major_topic = mesh_term.get('MajorTopic', False)

            mesh_id = f"mesh_{term.replace(' ', '_').lower()}"

            # Add MeSH node
            self.graph.add_node(
                mesh_id,
                type='mesh_term',
                term=term,
                major_topic=major_topic
            )

            # Add relationship
            self.graph.add_edge(
                pmcid, mesh_id,
                type='has_mesh_term',
                major_topic=major_topic
            )

    def extract_entities_from_text(self, pmcid: str, paper_dict: Dict):
        """Extract named entities from paper text using simple pattern matching."""
        # This is a simplified example - in practice you'd use NLP libraries like spaCy

        combined_text = ' '.join([
            ' '.join(paper_dict.get('Abstract', {}).values()),
            paper_dict.get('Body', {}).get('Introduction', ''),
            paper_dict.get('Body', {}).get('Methods', '')
        ])

        # Simple gene/protein pattern matching
        import re
        gene_patterns = [
            r'\b[A-Z]{2,}[0-9]+\b',  # Gene symbols like TP53, BRCA1
            r'\bp53\b', r'\bBRCA[12]\b',  # Specific important genes
        ]

        for pattern in gene_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in set(matches):  # Remove duplicates
                gene_id = f"gene_{match.lower()}"

                self.graph.add_node(
                    gene_id,
                    type='gene',
                    symbol=match.upper()
                )

                self.graph.add_edge(
                    pmcid, gene_id,
                    type='mentions_gene'
                )

    def analyze_graph_metrics(self) -> Dict[str, Any]:
        """Analyze knowledge graph metrics."""
        metrics = {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'node_types': {},
            'edge_types': {},
            'connected_components': nx.number_weakly_connected_components(self.graph),
            'average_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes(),
            'density': nx.density(self.graph)
        }

        # Count node types
        for node, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'unknown')
            metrics['node_types'][node_type] = metrics['node_types'].get(node_type, 0) + 1

        # Count edge types
        for _, _, data in self.graph.edges(data=True):
            edge_type = data.get('type', 'unknown')
            metrics['edge_types'][edge_type] = metrics['edge_types'].get(edge_type, 0) + 1

        return metrics

    def find_research_communities(self) -> List[Set[str]]:
        """Find research communities using graph clustering."""
        # Convert to undirected for community detection
        undirected = self.graph.to_undirected()

        # Find communities (simplified example)
        try:
            import community  # python-louvain
            partition = community.best_partition(undirected)

            # Group nodes by community
            communities = {}
            for node, comm_id in partition.items():
                if comm_id not in communities:
                    communities[comm_id] = set()
                communities[comm_id].add(node)

            return list(communities.values())

        except ImportError:
            print("python-louvain not installed, using connected components instead")
            return list(nx.weakly_connected_components(self.graph))

    def export_for_visualization(self, filename: str = "research_graph.json"):
        """Export graph for visualization tools like D3.js or Gephi."""
        # Convert to JSON format suitable for D3.js
        nodes = []
        links = []

        for node, data in self.graph.nodes(data=True):
            nodes.append({
                'id': node,
                'type': data.get('type', 'unknown'),
                'label': data.get('name', data.get('title', node)),
                **data
            })

        for source, target, data in self.graph.edges(data=True):
            links.append({
                'source': source,
                'target': target,
                'type': data.get('type', 'unknown'),
                **data
            })

        graph_data = {
            'nodes': nodes,
            'links': links,
            'metadata': self.analyze_graph_metrics()
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, default=str)

        print(f"Graph exported to {filename}")

# Usage example
kg = ResearchKnowledgeGraph(email="researcher@university.edu")

# Build knowledge graph
pmc_ids = ["7181753", "3539614", "5454911"]
graph = kg.build_graph_from_papers(pmc_ids)

# Analyze the graph
metrics = kg.analyze_graph_metrics()
print(f"Knowledge graph: {metrics['total_nodes']} nodes, {metrics['total_edges']} edges")

# Find research communities
communities = kg.find_research_communities()
print(f"Found {len(communities)} research communities")

# Export for visualization
kg.export_for_visualization("research_knowledge_graph.json")
```

These advanced examples demonstrate the flexibility and power of PMCGrab for sophisticated research workflows. You can adapt and combine these patterns to build custom research data processing pipelines tailored to your specific needs.
