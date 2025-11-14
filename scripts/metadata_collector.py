import os
import json


def create_metadata(paper):
    """
    Convert an arxiv.Result object into a metadata dictionary.
    """
    arxiv_id = paper.get_short_id()         # e.g. '2305.00633v4'
    base_id = arxiv_id.split('v')[0]        # e.g. '2305.00633'
    version = int(arxiv_id.split('v')[1])   # e.g. 4

    # Generate all version URLs if version > 1
    if version > 1:
        pdf_urls = [f"http://arxiv.org/pdf/{base_id}v{i}" for i in range(1, version + 1)]
    else:
        pdf_urls = [f"http://arxiv.org/pdf/{arxiv_id}"]

    metadata = {
        "arxiv_id": base_id,
        "paper_title": paper.title.strip(),
        "authors": [author.name for author in paper.authors],
        "submission_date": paper.published.strftime("%Y-%m-%d"),
        "revised_dates": [
            paper.updated.strftime("%Y-%m-%d")
        ] if paper.updated != paper.published else [],
        "latest_version": version,
        "categories": paper.categories,
        "abstract": paper.summary.strip(),
        "pdf_urls": pdf_urls
    }

    # Optional metadata fields
    if paper.comment:
        metadata["publication_venue"] = paper.comment.strip()
    else:
        metadata["publication_venue"] = None

    if paper.doi:
        metadata["doi"] = paper.doi

    return metadata


def save_metadata(paper, folder):
    """
    Save metadata.json for a single paper into the given folder.
    """
    metadata = create_metadata(paper)

    folder_path = os.path.abspath(folder)
    os.makedirs(folder_path, exist_ok=True)
    save_path = os.path.join(folder_path, "metadata.json")

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    print(f"💾 Saved metadata to {save_path}")
    return metadata
