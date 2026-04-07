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
        d_str = val.split('T')[0]
        try:
            return datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            return datetime.strptime(d_str, "%d-%m-%Y").date()
    except (ValueError, TypeError):
        return None
