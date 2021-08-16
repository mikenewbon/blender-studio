"""Display samples data as charts."""
import datetime
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, IntegerField
from django.db.models.functions import TruncDay
from django.shortcuts import render

from stats.models import Sample


def index(request):
    """Display stats for subscribers count."""
    time_threshold = datetime.datetime.now() - datetime.timedelta(days=365)
    count_per_day_q = (
        Sample.objects.filter(timestamp__gt=time_threshold)
        .annotate(date=TruncDay('timestamp'))
        .values('date')
        .annotate(y=Avg('value', output_field=IntegerField()))
        .order_by('date')
    )
    subscribers = count_per_day_q.filter(slug='users_subscribers_count')
    current_subscribers_count = subscribers.order_by('-date').first()['y']
    # blog_posts = count_per_day_q.filter(slug='blog_posts_count')
    chart_data = [
        {
            'type': 'line',
            'data': list(subscribers),
            'label': 'Subscribers',
            'borderColor': 'rgb(0,183,255)',
            'backgroundColor': 'rgba(0,183,255, 0.1)',
            'fill': True,
            'pointRadius': '0',
        },
    ]
    chart = {
        'datasets': json.dumps(chart_data, cls=DjangoJSONEncoder),
        'aggregate_by': 'day',
    }
    return render(
        request,
        'stats/index.html',
        {'chart': chart, 'current_subscribers_count': current_subscribers_count},
    )
