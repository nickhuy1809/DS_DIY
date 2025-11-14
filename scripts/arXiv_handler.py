import logging
logging.getLogger("arxiv").setLevel(logging.ERROR)   
import arxiv
import re

def get_ID(month, year, number):
    """Return arXiv ID in YYMM.NNNNN format."""
    return f"{year % 100:02d}{month:02d}.{number:05d}"

def id_exists(paper_id):
    """Check if a specific arXiv ID exists."""
    search = arxiv.Search(id_list=[paper_id])
    client = arxiv.Client(page_size=1, delay_seconds=0.2)
    try:
        next(client.results(search))
        return True
    except StopIteration:
        return False
    except Exception:
        # Network or parsing error — assume not found for safety
        return False

def find_first_id(year, month):
    """Find the first valid arXiv ID of a given month using exponential + binary search."""
    low, high = 1, 1
    # Exponential search upward until we find a valid ID
    while not id_exists(get_ID(month, year, high)):
        high *= 2
        if high > 99999:
            return None  # No valid papers this month

    # Now binary search between low and high to find the *first* valid ID
    while low + 1 < high:
        mid = (low + high) // 2
        if id_exists(get_ID(month, year, mid)):
            high = mid
        else:
            low = mid
    return high

def find_last_id(year, month):
    """Find the last valid arXiv ID of a given month."""
    low, high = 1, 1
    # Exponential search upward until we find a missing ID
    while id_exists(get_ID(month, year, high)):
        high *= 2
        if high > 99999:
            return 99999
    low = high // 2
    # Binary search for the last existing ID
    while low + 1 < high:
        mid = (low + high) // 2
        if id_exists(get_ID(month, year, mid)):
            low = mid
        else:
            high = mid
    return low

def get_IDs_month(month, year, start_number, end_number):
    """Get all valid arXiv IDs in a given month."""
    return [get_ID(month, year, i) for i in range(start_number, end_number + 1)]

def get_IDs_All(start_month, start_year, start_ID, end_month, end_year, end_ID):
    """Get all valid arXiv IDs in the given range."""
    ids = []
    y, m = start_year, start_month
    n_start = start_ID
    n_end = None
    while True:
        if y == end_year and m == end_month:
            n_end = end_ID
        else:
            n_end = find_last_id(y, m)
            if n_end is None:
                n_end = 0  # No papers this month

        if n_start <= n_end:
            ids.extend(get_IDs_month(m, y, n_start, n_end))

        if y == end_year and m == end_month:
            break
        m += 1
        if m > 12:
            m, y = 1, y + 1
        n_start = find_first_id(y, m)  # reset numbering

    return ids

def get_IDs_network(start_month, start_year, start_ID, end_month, end_year, end_ID, total_paper):
    """Get all valid arXiv IDs in the given range."""
    ids = []
    y, m = start_year, start_month
    n_start = start_ID
    n_end = None
    while True:
        if y == end_year and m == end_month:
            n_end = end_ID
        else:
            print(total_paper, start_ID, end_ID)
            n_end = total_paper - end_ID + start_ID - 1
            print(m, y)
            print(n_end)
            if n_end is None:
                n_end = 0  # No papers this month

        if n_start <= n_end:
            ids.extend(get_IDs_month(m, y, n_start, n_end))

        if y == end_year and m == end_month:
            break
        m += 1
        if m > 12:
            m, y = 1, y + 1
        n_start = 1  # reset numbering

    return ids


def format_arxiv_id_for_key(arxiv_id):
    """
    Convert arXiv ID from YYMM.NNNNN format to yyyymm-id format.
    Examples:
        2304.07856 -> 202304-07856
        1912.00123 -> 201912-00123
    """
    match = re.match(r'^(\d{2})(\d{2})\.(\d{5})$', arxiv_id)
    if match:
        yy, mm, id_num = match.groups()
        # Convert YY to YYYY (assuming 20YY for papers after 2000)
        yyyy = f"20{yy}"
        return f"{yyyy}{mm}-{id_num}"
    return arxiv_id  # Return as-is if format doesn't match

