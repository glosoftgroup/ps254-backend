from django.contrib import messages

from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.translation import pgettext_lazy
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from ..views import staff_member_required

from ...decorators import permission_decorator, user_trail
import logging

debug_logger = logging.getLogger('debug_logger')
info_logger  = logging.getLogger('info_logger')
error_logger = logging.getLogger('error_logger')

from django.contrib.auth import get_user_model
from ...userprofile.models import User

def notification_list(request):
    # read users notifications
    notifications = request.user.notifications.unread()
    users = User.objects.all().order_by('-id')
    ctx = {
        'notifications':notifications,
        'total_notifications': len(notifications),
        'users':User.objects.all()}
    return TemplateResponse(request,
                            'dashboard/notification/list.html',
                            ctx)


def write(request):
    if request.method == 'POST':
        subject = request.POST.get('subject')
        emailList = request.POST.get('emailList')
        body = request.POST.get('body')


    ctx = {'users':User.objects.all().order_by('-id')}
    return TemplateResponse(request,
                            'dashboard/notification/write.html',
                            ctx)
