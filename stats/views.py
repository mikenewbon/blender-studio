import datetime
from django.http import Http404
from django.shortcuts import render
from django.db.models import Count, Avg, Sum
from django.db.models.functions import TruncMonth, TruncYear
from stats.models import Sample


def index(request):
    """Display stats for subscribers count."""
    time_threshold = datetime.datetime.now() - datetime.timedelta(days=365)
    subscribers_by_month = (
        Sample.objects.filter(timestamp__gt=time_threshold)
        .annotate(month=TruncMonth('timestamp'))
        .values('month')
        .annotate(average_subscribers_count=Avg('users_subscribers_count'))
        .order_by('month')
    )

    # subscribers_by_month_series = []
    # for s in subscribers_by_month:
    #     subscribers_by_month_series.append({'t': s['month']})

    subscribers_by_month_series = [
        {'x': s['month'].strftime("%b %Y"), 'y': s['average_subscribers_count']}
        for s in subscribers_by_month
    ]
    # for f in subscribers_by_month_series:
    #     print(f)

    return render(
        request, 'stats/index.html', {'subscribers_by_month_series': subscribers_by_month_series}
    )
