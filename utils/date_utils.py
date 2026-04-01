from datetime import datetime

def parse_date(val):
    """
    Parses a date string into a date object.
    Handles 'YYYY-MM-DD' and 'YYYY-MM-DDTHH:MM:SS.sssZ'.
    """
    if not val:
        return None
    try:
        # Handles both "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS.sssZ"
        return datetime.strptime(val.split('T')[0], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
