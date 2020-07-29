from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe

from common.queries import get_activity_feed_page


@require_safe
def activity_feed(request: HttpRequest) -> HttpResponse:
    """
    Fetches a page of records to display in the recent activity feed.

    Records can be instances of: :model:`blog.Post`, :model:`ProductionLog`,
    or :model:`training.Training`.

    **Context**:
        ``records``
            A paginator Page object with dictionaries representing recently created objects.
            The dictionaries have the following keys:

            - 'pk': int - the primary key of the related object,
            - 'date_created': datetime - the date when the object was created,
            - 'obj_type': str - specifies the type (model) of the object,
            - 'object': a particular Model instance.

    **Template**
        :template:`common/components/blog_grid.html`
    """
    page_number = request.GET.get('page')
    per_page = request.GET.get('per_page')

    context = {'records': get_activity_feed_page(page_number, per_page)}

    return render(request, 'common/components/blog_grid.html', context)
