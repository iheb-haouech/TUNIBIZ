"""All date-only business rules use Tunisia's UTC+1 civil date."""
from datetime import datetime,timezone,timedelta
TUNIS=timezone(timedelta(hours=1))
def today(now=None):
 return (now or datetime.now(timezone.utc)).astimezone(TUNIS).date()
