import requests
import json
import os
import time
import re
from downloader import format_yymm_id

def get_paper_references(arxiv_id, delay=2):
    """
    Fetch references for a paper from Semantic Scholar API.
    
    Args:
        arxiv_id: arXiv ID (format: YYMM.NNNNN or YYMM.NNNNNvN)
        retry: number of retry attempts
        delay: delay between retries in seconds
    
    Returns:
        list: List of references with detailed information
    """
    # Clean arxiv_id (remove version suffix if present)
    clean_id = re.sub(r'v\d+$', '', arxiv_id)
    url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{clean_id}"
    params = {
        "fields": "references,references.title,references.authors,references.year,references.venue,references.externalIds,references.publicationDate"
    }

    while True:
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("references", [])
            elif response.status_code == 429:
                print(f"  Rate limit hit. Waiting {delay}s before retry...")
                time.sleep(delay)
            elif response.status_code == 404:
                print(f"  Paper {arxiv_id} not found in Semantic Scholar")
                return []
            else:
                print(f"  API returned status {response.status_code}, retrying in {delay}s...")
                time.sleep(delay)
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}, retrying in {delay}s...")
            time.sleep(delay)
 

def convert_to_references_dict(references):
    """
    Convert Semantic Scholar references to the required format:
    Dictionary with arXiv IDs as keys (in "yyyymm-id" format) for papers with arXiv IDs.
    For papers without arXiv IDs, use DOI or generate a unique key.
    
    Args:
        references: List of references from Semantic Scholar API
    
    Returns:
        dict: Dictionary with paper IDs as keys and metadata as values
    """
    result = {}
    non_arxiv_counter = 1
    
    for ref in references:
        # The reference data is directly in ref, not under "citedPaper"
        
        # Skip if reference is None or empty
        if not ref:
            continue
        
        # Extract external IDs (may be None)
        external_ids = ref.get("externalIds", {})
        if external_ids is None:
            external_ids = {}
        
        arxiv_id = external_ids.get("ArXiv", "")
        doi = external_ids.get("DOI", "")
        # Only keep references that have arXiv_id
        if not arxiv_id:
            continue
        
        # Determine the key for this reference
        if arxiv_id:
            # Use arXiv ID in yyyymm-id format
            key = format_yymm_id(arxiv_id)
        elif doi:
            # Use DOI as key (sanitize it)
            key = f"doi:{doi.replace('/', '_')}"
        else:
            # Generate a unique key for papers without arXiv ID or DOI
            title = ref.get("title", "")
            if title:
                # Use first word of title + counter
                first_word = re.sub(r'[^\w]', '', title.split()[0] if title.split() else "unknown")
                key = f"ref_{first_word[:20]}_{non_arxiv_counter}"
            else:
                key = f"ref_unknown_{non_arxiv_counter}"
            non_arxiv_counter += 1
        
        # Extract authors
        authors_list = ref.get("authors", [])
        authors = [author.get("name", "") for author in authors_list if author.get("name")]
        
        # Extract dates (use publicationDate if available)
        publication_date = ref.get("publicationDate", "")
        year = ref.get("year")
        
        # If no publication date but have year, create an ISO-like format
        if not publication_date and year:
            publication_date = f"{year}-01-01"  # Use Jan 1st as placeholder
        
        # Build metadata dictionary with required fields
        metadata = {
            "title": ref.get("title", ""),
            "authors": authors,
            "submission_date": publication_date if publication_date else "",
            "revised_dates": []  # Semantic Scholar doesn't provide revision history
        }
        
        # Add optional fields for reference
        if doi:
            metadata["doi"] = doi
        if arxiv_id:
            metadata["arxiv_id"] = arxiv_id
        if ref.get("venue"):
            metadata["venue"] = ref.get("venue")
        if year:
            metadata["year"] = year
        
        result[key] = metadata
    
    return result


def save_references(arxiv_id, paper_folder, verbose=True):
    """
    Fetch and save references for a paper version to both JSON and BibTeX formats.
    
    Args:
        arxiv_id: arXiv ID (e.g., "2304.07856v1")
        version_folder: Path to version folder (e.g., "data/2304.07856/v1/")
        verbose: Whether to print progress messages
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if the folder exists, if not, create it
    if not os.path.exists(paper_folder):
        os.makedirs(paper_folder, exist_ok=True)

    if verbose:
        print(f"Fetching references for {arxiv_id}...")

    references = get_paper_references(arxiv_id)

    if not references:
        if verbose:
            print(f"  No references found for {arxiv_id}")
        json_path = os.path.join(paper_folder, "references.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return False

    json_path = os.path.join(paper_folder, "references.json")
    references_dict = convert_to_references_dict(references)
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(references_dict, f, indent=2, ensure_ascii=False)
        if verbose:
            print(f"  Saved {len(references_dict)} references to references.json")
    except Exception as e:
        print(f"  Error saving JSON: {e}")
        return False
    


def extract_references_for_paper(paper_id, base_data_dir="../data"):
    """
    Extract references for all versions of a paper.
    
    Args:
        paper_id: arXiv paper ID without version (e.g., "2304.07856")
        base_data_dir: Base directory containing data folders
    
    Returns:
        dict: Statistics about the extraction
    """
    paper_id_key = format_yymm_id(paper_id)
    paper_folder = os.path.join(base_data_dir, paper_id_key)
    
    save_references(paper_id, os.path.join(paper_folder))
    
    