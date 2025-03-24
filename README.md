Use cron to execute pscbook.py for whenever you want to book a court. Bookings
open everyday at 8am. For example, if I want to book a court every Monday.

```
crontab -e
0 8 * * MON python pscbook.py
```
