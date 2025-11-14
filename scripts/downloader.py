import os
import re
import tarfile
import requests
import string
from metadata_collector import save_metadata

ARXIV_HOST = "https://arxiv.org"

def format_yymm_id(base_id: str) -> str:
    """'2303.07856' -> '2303-07856'"""
    return base_id.replace('.', '-')

def sanitize_filename(name: str) -> str:
    """
    Replace unsafe characters and limit path depth to avoid errors.
    Keeps only alphanumeric, underscores, hyphens, dots, and slashes.
    """
    safe_chars = f"-_.{string.ascii_letters}{string.digits}/"
    return ''.join(c if c in safe_chars else '_' for c in name)

def safe_extract_tar(tar_path: str, extract_to: str) -> None:
    """Safely extract a tar.gz file using 'filter=data', skipping broken entries."""
    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            for member in tar.getmembers():
                try:
                    # Skip symbolic links and absolute paths (security)
                    if member.islnk() or member.issym() or member.name.startswith("/") or ".." in member.name:
                        continue
                    
                    member.name = sanitize_filename(member.name)
                    target_path = os.path.join(extract_to, member.name)
                    target_dir = os.path.dirname(target_path)
                    os.makedirs(target_dir, exist_ok=True)

                    # Extract safely
                    tar.extract(member, path=extract_to, filter="data")
                except (FileNotFoundError, OSError, tarfile.ExtractError) as inner_e:
                    print(f"⚠️ Skipped bad entry in {os.path.basename(tar_path)}: {member.name} ({inner_e})")
                    continue
    except Exception as e:
        print(f"[Error] Extraction failed for {tar_path}: {e}")


def download_url(url: str, out_path: str) -> bool:
    """Basic downloader (no retry, no backoff)."""
    headers = {"User-Agent": "arxiv-downloader/1.0 (+https://github.com/your-handle)"}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            if r.status_code == 200:
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                return True
            print(f"HTTP {r.status_code} for {url}")
            return False
    except requests.RequestException as e:
        print(f"Download failed for {url}: {e}")
        return False


def cleanup_non_tex_bib_files(folder: str) -> None:
    """Remove all non-.tex and non-.bib files."""
    for root, _, files in os.walk(folder):
        for file in files:
            if not (file.endswith(".tex") or file.endswith(".bib")):
                try:
                    os.remove(os.path.join(root, file))
                except OSError as e:
                    print(f"Warning: could not remove {file}: {e}")


def download(list_download: list, base_dir: str) -> None:
    """
    Downloads all versions of an arXiv paper using /src/{id} URL.
    Extracts .tex/.bib files and saves metadata.
    """
    if not list_download:
        print("⚠️ list_download is empty — skipping.")
        return

    match = re.match(r"^(\d{4}\.\d{5})", list_download[0].get_short_id())
    if not match:
        print(f"Invalid arXiv ID format: {list_download[0].get_short_id()}")
        return

    arxiv_id = match.group(1)
    folder_arxiv = os.path.join(base_dir, format_yymm_id(arxiv_id))
    print(f"Processing {arxiv_id} → {folder_arxiv}")

    os.makedirs(folder_arxiv, exist_ok=True)
    tex_root = os.path.join(folder_arxiv, "tex")
    os.makedirs(tex_root, exist_ok=True)

    for result in list_download:
        full_id = result.get_short_id()  # e.g. '2305.00633v4'
        folder_version = os.path.join(tex_root, full_id)  # put all versions under .../<paper>/tex/<version>
        os.makedirs(folder_version, exist_ok=True)

        src_url = f"{ARXIV_HOST}/src/{full_id}"
        tar_path = os.path.join(folder_version, f"{full_id}.tar.gz")
        print(f"Attempting source: {src_url}")

        if not download_url(src_url, tar_path):
            print(f"Source unavailable for {full_id}")
            continue

        # Validate and extract
        if not tarfile.is_tarfile(tar_path):
            print(f"Invalid tar archive for {full_id}. Removing file.")
            try:
                os.remove(tar_path)
            except OSError as e:
                print(f"Could not remove invalid file {tar_path}: {e}")
            continue

        try:
            safe_extract_tar(tar_path, folder_version)
            cleanup_non_tex_bib_files(folder_version)
            print(f"✅ Extracted to {folder_version}")
        except Exception as e:
            print(f"⚠️ Extraction failed for {full_id}: {e}")
        finally:
            try:
                os.remove(tar_path)
            except OSError:
                pass

    # Save metadata after all versions
    try:
        save_metadata(result, folder_arxiv)
    except Exception as e:
        print(f"⚠️ Metadata save failed for {arxiv_id}: {e}")
