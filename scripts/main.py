import threading
import queue
import time
import arxiv
from arXiv_handler import get_IDs_All, get_IDs_network
from downloader import download
from reference_extractor import extract_references_for_paper
import os
import random


def fetch_ids_worker(start_month, start_year, start_ID, end_month, end_year, end_ID, total_paper, start_index, num_papers, id_queue):
    print("[Step 1] Fetching arXiv IDs...")
    #ids = get_IDs_All(start_month, start_year, start_ID, end_month, end_year, end_ID)
    ids = get_IDs_network(start_month, start_year, start_ID, end_month, end_year, end_ID, total_paper)
    selected_ids = ids[start_index:start_index + num_papers]
    print(f"[Step 1] Fetched {len(selected_ids)} IDs.")
    for arxiv_id in selected_ids:
        id_queue.put(arxiv_id)
    for _ in range(DOWNLOAD_THREAD_COUNT):
        id_queue.put(None)


def download_with_retries(client, arxiv_id, max_retries=5):
    """Try downloading paper metadata with exponential backoff for 429/503 errors."""
    for attempt in range(max_retries):
        try:
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(client.results(search))
            return result
        except Exception as e:
            error_str = str(e)
            if "HTTP 429" in error_str or "HTTP 503" in error_str:
                wait_time = min(60 * (2 ** attempt), 600)  # exponential backoff (up to 10 min)
                jitter = random.uniform(0, 5)
                print(f"[Download] Server busy ({error_str}). Retrying {arxiv_id} in {wait_time + jitter:.1f}s...")
                time.sleep(wait_time + jitter)
                continue
            else:
                raise  # rethrow unexpected errors
    raise RuntimeError(f"[Download] Failed after {max_retries} retries for {arxiv_id}")


def download_worker(id_queue, download_queue, base_data_dir, delay=2):
    client = arxiv.Client()
    processed = 0
    while True:
        arxiv_id = id_queue.get()
        if arxiv_id is None:
            download_queue.put(None)
            print(f"[Download] Thread finished. Total papers downloaded: {processed}")
            break

        try:
            print(f"[Download] Starting: {arxiv_id}")
            result_latest = download_with_retries(client, arxiv_id)

            # Determine latest version number
            version_latest = int(result_latest.get_short_id().split('v')[1])
            list_download = [result_latest]

            # Download older versions
            for v in range(1, version_latest):
                arxiv_id_v = f"{arxiv_id}v{v}"
                result_v = download_with_retries(client, arxiv_id_v)
                list_download.append(result_v)

            # Extract & clean
            download(list_download, base_data_dir)
            processed += 1
            print(f"[Download] Finished: {arxiv_id} (Total: {processed})")
            download_queue.put(arxiv_id)
            time.sleep(delay)  # Respect API rate

        except Exception as e:
            print(f"[Download] Error for {arxiv_id}: {e}")
            continue


def reference_worker(download_queue, base_data_dir, delay=2):
    processed = 0
    while True:
        arxiv_id = download_queue.get()
        if arxiv_id is None:
            print(f"[Reference] Thread finished. Total papers processed: {processed}")
            break
        try:
            print(f"[Reference] Starting: {arxiv_id}")
            extract_references_for_paper(arxiv_id, base_data_dir)
            processed += 1
            print(f"[Reference] Finished: {arxiv_id} (Total: {processed})")
            time.sleep(delay)
        except Exception as e:
            print(f"[Reference] Error for {arxiv_id}: {e}")
            continue


if __name__ == "__main__":
    start_month = 3
    start_year = 2023
    start_ID = 7856
    end_month = 4
    end_year = 2023
    end_ID = 4606
    total_paper = 15000
    base_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "23127130"))
    os.makedirs(base_data_dir, exist_ok=True)

    start_index = 4000
    num_papers = 1000

    DOWNLOAD_THREAD_COUNT = 3
    REFERENCE_THREAD_COUNT = 2

    id_queue = queue.Queue(maxsize=DOWNLOAD_THREAD_COUNT * 2)
    download_queue = queue.Queue(maxsize=REFERENCE_THREAD_COUNT * 2)

    start_time = time.time()
    print("Starting pipeline...")

    t1 = threading.Thread(target=fetch_ids_worker, args=(
        start_month, start_year, start_ID, end_month, end_year, end_ID, total_paper, start_index, num_papers, id_queue))
    t1.start()

    download_threads = []
    for _ in range(DOWNLOAD_THREAD_COUNT):
        t = threading.Thread(target=download_worker, args=(id_queue, download_queue, base_data_dir, 2))
        t.start()
        download_threads.append(t)

    reference_threads = []
    for _ in range(REFERENCE_THREAD_COUNT):
        t = threading.Thread(target=reference_worker, args=(download_queue, base_data_dir, 2))
        t.start()
        reference_threads.append(t)

    t1.join()
    for t in download_threads:
        t.join()
    for t in reference_threads:
        t.join()

    end_time = time.time()
    print(f"Pipeline complete. Total time: {end_time - start_time:.2f} seconds")
