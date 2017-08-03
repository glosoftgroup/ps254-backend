from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.translation import pgettext_lazy
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator, PageNotAnInteger, InvalidPage, EmptyPage

from ...core.utils import get_paginator_items
from ..views import staff_member_required
from ...userprofile.models import User, UserTrail
from ...customer.models import Customer
from ...supplier.models import Supplier, AddressBook

from ...decorators import permission_decorator, user_trail
import logging

debug_logger = logging.getLogger('debug_logger')
info_logger = logging.getLogger('info_logger')
error_logger = logging.getLogger('error_logger')


def users(request):
	try:
		users = Supplier.objects.all().order_by('-id')
		page = request.GET.get('page', 1)
		paginator = Paginator(users, 10)
		try:
			users = paginator.page(page)
		except PageNotAnInteger:
			users = paginator.page(1)
		except InvalidPage:
			users = paginator.page(1)
		except EmptyPage:
			users = paginator.page(paginator.num_pages)
		user_trail(request.user.name, 'accessed suppliers list page', 'view')
		info_logger.info('User: ' + str(request.user.name) + ' accessed the view users page')
		if request.GET.get('initial'):
			return HttpResponse(paginator.num_pages)
		else:
			ctx = {'users': users, 'pn': paginator.num_pages}
			return TemplateResponse(request, 'dashboard/supplier/pagination/users2.html', ctx)
	except TypeError as e:
		error_logger.error(e)
		return HttpResponse('error accessing users')

@staff_member_required
def user_paginate(request):
	page = int(request.GET.get('page', 1))
	list_sz = request.GET.get('size')
	p2_sz = request.GET.get('psize')
	select_sz = request.GET.get('select_size')
	if request.GET.get('gid'):
		users = Supplier.objects.filter(groups__id=request.GET.get('gid'))
		if p2_sz:
			paginator = Paginator(users, int(p2_sz))
			users = paginator.page(page)
			return TemplateResponse(request,'dashboard/supplier/pagination/paginate.html',{'users':users})

		paginator = Paginator(users, 10)
		users = paginator.page(page)
		return TemplateResponse(request,'dashboard/supplier/pagination/p2.html',{'users':users, 'pn':paginator.num_pages,'sz':10,'gid':request.GET.get('gid')})

	else:
		users = Supplier.objects.all().order_by('-id')
		if list_sz:
			paginator = Paginator(users, int(list_sz))
			users = paginator.page(page)
			return TemplateResponse(request,'dashboard/supplier/pagination/p2.html',{'users':users, 'pn':paginator.num_pages,'sz':list_sz, 'gid':0})
		else:
			paginator = Paginator(users, 10)
		if p2_sz:
			paginator = Paginator(users, int(p2_sz))
			users = paginator.page(page)
			return TemplateResponse(request,'dashboard/supplier/pagination/paginate.html',{'users':users})

		try:
			users = paginator.page(page)
		except PageNotAnInteger:
			users = paginator.page(1)
		except InvalidPage:
			groups = paginator.page(1)
		except EmptyPage:
			users = paginator.page(paginator.num_pages)
		return TemplateResponse(request,'dashboard/supplier/pagination/paginate.html',{'users':users})


@staff_member_required
def user_search(request):
	if request.is_ajax():
		page = request.GET.get('page', 1)
		list_sz = request.GET.get('size', 10)
		p2_sz = request.GET.get('psize')
		q = request.GET.get('q')
		if list_sz is None:
			sz = 10
		else:
			sz = list_sz

		if q is not None:
			users = Supplier.objects.filter(
				Q(name__icontains=q) |
				Q(email__icontains=q) | Q(mobile__icontains=q)).order_by('id')
			paginator = Paginator(users, 10)
			try:
				users = paginator.page(page)
			except PageNotAnInteger:
				users = paginator.page(1)
			except InvalidPage:
				users = paginator.page(1)
			except EmptyPage:
				users = paginator.page(paginator.num_pages)
			if p2_sz:
				users = paginator.page(page)
				return TemplateResponse(request, 'dashboard/supplier/pagination/paginate.html', {'users': users})

			return TemplateResponse(request, 'dashboard/supplier/pagination/search.html',
									{'users': users, 'pn': paginator.num_pages, 'sz': sz, 'q': q})

@staff_member_required
@permission_decorator('userprofile.add_user')
def user_add(request):
	try:
		permissions = Permission.objects.all()
		groups = Group.objects.all()
		user_trail(request.user.name, 'accessed add supplier page','view')
		info_logger.info('User: '+str(request.user.name)+' accessed supplier create page')
		return TemplateResponse(request, 'dashboard/supplier/add_user.html',{'permissions':permissions, 'groups':groups})
	except TypeError as e:
		error_logger.error(e)
		return HttpResponse('error accessing add users page')

@staff_member_required
def supplier_add_modal(request):
	try:
		return TemplateResponse(request, 'dashboard/supplier/_modal_add_supplier.html', {})
	except Exception as e:
		error_logger.error(e)
		return HttpResponse('error accessing add suppliers page')

@staff_member_required
def supplier_add(request):
	try:
		return TemplateResponse(request, 'dashboard/supplier/add_supplier.html',{})
	except Exception as e:
		error_logger.error(e)
		return HttpResponse('error accessing add suppliers page')
@staff_member_required
def fetch_suppliers(request):
	suppliers = Supplier.objects.all()
	ctx = {'suppliers':suppliers}
	return TemplateResponse(request, 'dashboard/supplier/refreshed_supplier.html',ctx)
@staff_member_required
@csrf_exempt
def user_process(request):
	user = Supplier.objects.all()
	if request.method == 'POST':
		name = request.POST.get('name')
		email = request.POST.get('email')
		code = request.POST.get('code')
		fax = request.POST.get('fax')
		city = request.POST.get('city')
		website = request.POST.get('website','')		
		street1 = request.POST.get('street1')
		street2 = request.POST.get('street2')
		mobile = request.POST.get('mobile')
		image= request.FILES.get('image')
		groups = request.POST.getlist('groups[]')
		new_user = Supplier.objects.create(
			name = name,
			email = email,			
			code = code,
			fax = fax,
			city = city,
			website = website,
			street1 = street1,
			street2 = street2,
			mobile = mobile,
			image = image
		)
		try:
			new_user.save()
		except:
			error_logger.info('Error when saving ')
		last_id = Supplier.objects.latest('id')
		if groups:
			permissions = Permission.objects.filter(group__name__in=groups)
			last_id.user_permissions.add(*permissions)
			gps = Group.objects.filter(name__in=groups)
			last_id.groups.add(*gps)
			last_id.save()
		user_trail(request.user.name, 'created user: '+str(name),'add')
		info_logger.info('User: '+str(request.user.name)+' created user:'+str(name))
		return HttpResponse(last_id.id)

def user_detail(request, pk):
	user = get_object_or_404(Supplier, pk=pk)
	
	return TemplateResponse(request, 'dashboard/supplier/detail.html', {'user':user})

def user_delete(request, pk):
	user = get_object_or_404(Supplier, pk=pk)
	if request.method == 'POST':
		user.delete()
		user_trail(request.user.name, 'deleted supplier: '+ str(user.name))
		return HttpResponse('success')
def user_edit(request, pk):
	user = get_object_or_404(Supplier, pk=pk)
	#addresses = user.get_address()		
	ctx = {'user': user}
	user_trail(request.user.name, 'accessed edit page for supplier '+ str(user.name),'update')
	info_logger.info('User: '+str(request.user.name)+' accessed edit page for supplier: '+str(user.name))
	return TemplateResponse(request, 'dashboard/supplier/edit_user.html', ctx)

def user_update(request, pk):
	user = get_object_or_404(Supplier, pk=pk)
	if request.method == 'POST':
		name = request.POST.get('name')
		email = request.POST.get('email')		
		code = request.POST.get('code')
		fax = request.POST.get('fax')
		city = request.POST.get('city')
		website = request.POST.get('website','')		
		street1 = request.POST.get('street1')
		street2 = request.POST.get('street2')
		mobile = request.POST.get('mobile')
		image= request.FILES.get('image')		
		if image :
			user.name = name
			user.email = email			
			user.code = code
			user.fax = fax
			user.city = city
			user.website = website
			user.street2 = street2
			user.street1 = street1
			user.mobile = mobile
			user.image = image
			user.save()
			user_trail(request.user.name, 'updated supplier: '+ str(user.name))
			info_logger.info('User: '+str(request.user.name)+' updated supplier: '+str(user.name))
			return HttpResponse("success with image")
		else:
			user.name = name
			user.email = email			
			user.code = code
			user.fax = fax
			user.city = city
			user.website = website
			user.street2 = street2
			user.street1 = street1
			user.mobile = mobile
			user.save()
			user_trail(request.user.name, 'updated supplier: '+ str(user.name))
			info_logger.info('User: '+str(request.user.name)+' updated supplier: '+str(user.name))
			return HttpResponse("success without image")

@csrf_exempt
def user_assign_permission(request):
	if request.method == 'POST':
		user_id = request.POST.get('user_id')
		user = get_object_or_404(User, pk=user_id)
		user_has_permissions = Permission.objects.filter(user=user)
		login_status = request.POST.get('check_login')
		permission_list = request.POST.getlist('checklist[]')
		if login_status == 'inactive':
			user.is_staff = False
			user.is_active = False
			user.user_permissions.remove(*user_has_permissions)
			user.save()
			user_trail(request.user.name, 'deactivated and removed all permissions for user: '+ str(user.name))
			info_logger.info('User: '+str(request.user.name)+' deactivated and removed all permissions for user: '+str(user.name))
			return HttpResponse('deactivated')
		else:
			if user_has_permissions in permission_list:
				not_in_user_permissions = list(set(permission_list) - set(user_has_permissions))
				user.is_staff = True
				user.is_active = True
				user.user_permissions.add(*not_in_user_permissions)
				user.save()
				user_trail(request.user.name, 'assigned permissions for user: '+ str(user.name))
				info_logger.info('User: '+str(request.user)+' assigned permissions for user: '+str(user.name))
				return HttpResponse('permissions added')
			else:
				not_in_user_permissions = list(set(permission_list) - set(user_has_permissions))
				user.is_staff = True
				user.is_active = True
				user.user_permissions.remove(*user_has_permissions)
				user.user_permissions.add(*not_in_user_permissions)
				user.save()
				user_trail(request.user.name, 'assigned permissions for user: '+ str(user.name))
				info_logger.info('User: '+str(request.user.name)+' assigned permissions for user: '+str(user.name))
				return HttpResponse('permissions updated')

@staff_member_required
def address_add(request,pk):
	if request.is_ajax():
		if request.method == 'GET':			
			if pk:
				pk = pk
			ctx = {'supplier_pk':pk}
			return TemplateResponse(request, 'dashboard/supplier/_address_add.html', ctx)
		if request.method == 'POST':
			city = request.POST.get('city')
			email = request.POST.get('email')
			postal_code = request.POST.get('postal_code')
			phone = request.POST.get('phone')
			first_name = request.POST.get('first_name')
			last_name = request.POST.get('last_name')
			contact_name = request.POST.get('contact_name')
			job_position = request.POST.get('job_position')
			supplier = get_object_or_404(Supplier, pk=pk)
			address = AddressBook.objects.create(
								city=city,
								email=email,
								postal_code =postal_code,
								phone = phone,
								first_name=first_name,
								last_name=last_name,
								contact_name=contact_name,
								job_position=job_position
								)
			address.save()			

			supplier.addresses.add(address)			
			
			ctx = {'address': address}
    		return TemplateResponse(request,
                            'dashboard/supplier/_newContact.html',
                            ctx)
			
@staff_member_required
def refresh_contact(request, pk=None):
	if request.method == 'GET':
		if pk:
			user = get_object_or_404(Supplier, pk=pk)
			ctx = {'user': user}
			return TemplateResponse(request,
                            'dashboard/supplier/_newContact.html',
                            ctx)
	return HttpResponse('Post request not accepted')
@staff_member_required
def contact_delete(request, pk):
    address = get_object_or_404(AddressBook, pk=pk)
    if request.method == 'POST':
        address.delete()
        messages.success(
            request,
            pgettext_lazy(
                'Dashboard message', 'Deleted contact %s') % address)
        if pk:
            if request.is_ajax():
            	script = "'#tr"+str(pk)+"'"
                return HttpResponse(script)
    ctx = {'address': address}
    return TemplateResponse(request,
                            'dashboard/supplier/modal_delete.html',
                            ctx)			
def user_trails(request):
	users = UserTrail.objects.all().order_by('id')
	user_trail(request.user.name, 'accessed user trail page')
	info_logger.info('User: '+str(request.user.name)+' accessed the user trail page')
	return TemplateResponse(request, 'dashboard/users/trail.html', {'users':users})




		