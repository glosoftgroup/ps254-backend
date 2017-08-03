from __future__ import unicode_literals

import emailit.api
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.utils.translation import pgettext_lazy
from django.views.decorators.http import require_http_methods
from django.contrib.postgres.search import SearchVector

from . import forms
from ...core.utils import get_paginator_items
from ...purchase.models import (
								PurchaseOrder,
								PurchaseItems,
								PurchaseProduct
								)
from ...supplier.models import Supplier
from ...product.models import (Product, ProductAttribute, Category,
							   ProductClass, AttributeChoiceValue,
							   ProductImage, ProductVariant, Stock,
							   StockLocation, ProductTax, StockHistoryEntry)
from ..views import staff_member_required
from ..views import get_low_stock_products
from django.http import HttpResponse
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from ...decorators import permission_decorator, user_trail
import logging

debug_logger = logging.getLogger('debug_logger')
info_logger = logging.getLogger('info_logger')
error_logger = logging.getLogger('error_logger')

@staff_member_required
def re_order(request):
	low_stock = get_low_stock_products()
	ctx = {"low_stock":low_stock}
	user_trail(request.user.name, 'accessed reorder page', 'view')
	info_logger.info('User: '+str(request.user.name)+' accessed reorder page')
	return TemplateResponse(request, 'dashboard/re_order/re_order.html', ctx)    

import json
@staff_member_required
@permission_decorator('product.add_stock')
def add_reorder_stock(request,pk=None):	
	if request.is_ajax():
		if request.POST.getlist('variants[]'):			
			variants = request.POST.get('variants[]')
			supplier = get_object_or_404(Supplier,name=str(request.POST.get('supplier')))		
			product = get_object_or_404(Product,pk=(request.POST.get('pid')))		

			ref_no   = request.POST.get('ref_no')
			if supplier:
				purchase_order = PurchaseOrder.objects.create(
														product=product,					
														supplier=supplier,
														lfo_number=ref_no,
														user=request.user,)

				items = json.loads(variants)
				print purchase_order
				for li in items:
					var = ProductVariant.objects.get(pk=int(li['id']))
					sku = var.sku
					x = PurchaseItems.objects.create(
												purchase_order=purchase_order,
												sku=sku,
												quantity=int(li['quantity']),
												product_name=str(li['name']))
					x.save()

					  
			return HttpResponse('success!')
		variant_id = request.POST.get('variant_id')
		#return HttpResponse(variant_id)
		variant = ProductVariant.objects.get(pk=int(variant_id))
		ctx = {"variant":variant}
		user_trail(request.user.name, 'added reorder level', 'add')
		info_logger.info('User: ' + str(request.user.name) + ' added reorder level')
		return TemplateResponse(request, 'dashboard/re_order/_order.html', ctx)    


@staff_member_required
def request_order(request):
	if request.POST.get('supplier'):
		supplier = Supplier.objects.get(pk=int(request.POST.get('supplier')))
		context = {'user': request.user.name}
		purchase_order = PurchaseOrder.objects.get(pk=int(request.POST.get('order_id')))		

		send_email = emailit.api.send_mail(
			supplier.email, context, 'order/emails/confirm_email',
			from_email=settings.ORDER_FROM_EMAIL)
		# if send_email:
		# 	if purchase_order:
		# 	         purchase_order.change_status('sent')
		return HttpResponse(send_email)
	return HttpResponse('Bad request')

@staff_member_required
def re_order_form(request, pk):
	product = get_object_or_404(Product.objects.prefetch_related(
			'images', 'variants'), pk=pk)	
	suppliers = Supplier.objects.all()
	variants = product.variants.all()
	edit_variant = not product.product_class.has_variants
	
	attributes = product.product_class.variant_attributes.prefetch_related(
		'values')
	qset = PurchaseOrder.objects.filter(product=product)
	if qset.exists():
		for q in qset:
			qset = q
			items = PurchaseItems.objects.filter(purchase_order=q)
			print items
		ctx = {'items':items,'order':qset,"product":product,'suppliers':suppliers,'variants':variants,'attributes':attributes}
	else:
		ctx = {"product":product,'suppliers':suppliers,'variants':variants,'attributes':attributes}
	return TemplateResponse(request, 'dashboard/re_order/re_order_form.html', ctx)    

# @staff_member_required
# @permission_decorator('product.view_productclass')
# def product_class_list(request):
# 	classes = ProductClass.objects.all().prefetch_related(
# 		'product_attributes', 'variant_attributes').order_by('-id')
# 	form = forms.ProductClassForm(request.POST or None)
# 	if form.is_valid():
# 		return redirect('dashboard:product-class-add')
# 	classes = get_paginator_items(classes, 30, request.GET.get('page'))
# 	classes.object_list = [
# 		(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
# 		 pc.variant_attributes.all())
# 		for pc in classes.object_list]
# 	ctx = {'form': form, 'product_classes': classes}
# 	return TemplateResponse(request, 'dashboard/product/class_list.html', ctx)

@staff_member_required
def class_list_view(request):
	try:
		queryset_list = ProductClass.objects.all().prefetch_related(
			'product_attributes', 'variant_attributes').order_by('-id')

		page = request.GET.get('page', 1)
		paginator = Paginator(queryset_list, 10)
		try:
			queryset_list = paginator.page(page)
		except PageNotAnInteger:
			queryset_list = paginator.page(1)
		except InvalidPage:
			queryset_list = paginator.page(1)
		except EmptyPage:
			queryset_list = paginator.page(paginator.num_pages)
		product_results = queryset_list
		product_results.object_list = [
			(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
			 pc.variant_attributes.all())
			for pc in product_results.object_list]
		user_trail(request.user.name, 'accessed the roles page','view')
		info_logger.info('User: '+str(request.user.name)+' accessed the roles page page')

		data ={
			'classes':product_results,
			'totalp':paginator.num_pages
			   }
		if request.GET.get('initial'):
			return HttpResponse(paginator.num_pages)
		else:
			return TemplateResponse(request, 'dashboard/product/subcategory/view.html', data)
	except TypeError as e:
		error_logger.error(e)
		return HttpResponse('error accessing users')

def paginate_class_list(request):
	page = int(request.GET.get('page', 1))
	list_sz = request.GET.get('size')
	p2_sz = request.GET.get('psize')
	select_sz = request.GET.get('select_size')

	try:
		queryset_list =ProductClass.objects.all().prefetch_related(
			'product_attributes', 'variant_attributes').order_by('-id')

		if list_sz:
			paginator = Paginator(queryset_list, int(list_sz))
			queryset_list = paginator.page(page)
			product_results = queryset_list
			product_results.object_list = [
				(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
				 pc.variant_attributes.all())
				for pc in product_results.object_list]
			data = {
				'classes': product_results,
				'pn': paginator.num_pages,
				'sz': list_sz,
				'gid': 0
			}
			return TemplateResponse(request, 'dashboard/product/subcategory/p2.html', data)
		else:
			paginator = Paginator(queryset_list, 10)
			if p2_sz:
				paginator = Paginator(queryset_list, int(p2_sz))
			queryset_list = paginator.page(page)
			product_results = queryset_list
			product_results.object_list = [
				(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
				 pc.variant_attributes.all())
				for pc in product_results.object_list]
			data = {
				'classes': product_results,
			}
			return TemplateResponse(request, 'dashboard/product/subcategory/paginate.html', data)

		try:
			queryset_list = paginator.page(page)
		except PageNotAnInteger:
			queryset_list = paginator.page(1)
		except InvalidPage:
			queryset_list = paginator.page(1)
		except EmptyPage:
			queryset_list = paginator.page(paginator.num_pages)
		product_results = queryset_list
		product_results.object_list = [
			(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
			 pc.variant_attributes.all())
			for pc in product_results.object_list]
		return TemplateResponse(request, 'dashboard/product/subcategory/paginate.html', {'classes': product_results})
	except Exception, e:
		return  HttpResponse()

@staff_member_required
def search_class_list(request):
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
			queryset_list = ProductClass.objects.filter(name__icontains=q).prefetch_related(
				'product_attributes', 'variant_attributes').order_by('-id')
			paginator = Paginator(queryset_list, 10)

			try:
				queryset_list = paginator.page(page)
			except PageNotAnInteger:
				queryset_list = paginator.page(1)
			except InvalidPage:
				queryset_list = paginator.page(1)
			except EmptyPage:
				queryset_list = paginator.page(paginator.num_pages)
			product_results = queryset_list
			product_results.object_list = [
				(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
				 pc.variant_attributes.all())
				for pc in product_results.object_list]
			if p2_sz:
				queryset_list = paginator.page(page)
				return TemplateResponse(request, 'dashboard/product/subcategory/paginate.html', {'classes': product_results})

			return TemplateResponse(request, 'dashboard/product/subcategory/search.html',
									{'classes':product_results, 'pn': paginator.num_pages, 'sz': sz, 'q': q})

@staff_member_required
def product_class_create(request,new_window=None):
	product_class = ProductClass()
	form = forms.ProductClassForm(request.POST or None,
								  instance=product_class)
	if form.is_valid():
		try:
			product_class = form.save()
			return HttpResponse('success')
		except Exception, e:
			return HttpResponse(e)
		msg = pgettext_lazy(
			'Dashboard message', 'Added product sub category %s') % product_class
		messages.success(request, msg)
		if new_window:
			return HttpResponse('<script>function closeme(){ window.opener.refreshProductType(); window.close();} closeme();</script>')
		# return redirect('dashboard:product-class-list')
	ctx = {'form': form, 'product_class': product_class}
	if request.is_ajax():
		return TemplateResponse(request, 'dashboard/product/product_class_form_ajax.html', ctx)
	return TemplateResponse(
		request, 'dashboard/product/product_class_form.html', ctx)


@staff_member_required
@permission_decorator('product.change_productclass')
def product_class_edit(request, pk):
	product_class = get_object_or_404(
		ProductClass, pk=pk)
	form = forms.ProductClassForm(request.POST or None,
								  instance=product_class)
	if form.is_valid():
		product_class = form.save()
		msg = pgettext_lazy(
			'Dashboard message', 'Updated product type %s') % product_class
		messages.success(request, msg)
		return redirect('dashboard:product-class-update', pk=pk)
	ctx = {'form': form, 'product_class': product_class}
	
	return TemplateResponse(
		request, 'dashboard/product/product_class_form.html', ctx)


@staff_member_required
@permission_decorator('product.delete_productclass')
def product_class_delete(request, pk):
	product_class = get_object_or_404(ProductClass, pk=pk)
	products = [str(p) for p in product_class.products.all()]
	if request.method == 'POST':
		product_class.delete()
		messages.success(
			request,
			pgettext_lazy(
				'Dashboard message',
				'Deleted product type %s') % product_class)
		return redirect('dashboard:product-class-list')
	return TemplateResponse(
		request,
		'dashboard/product/modal_product_class_confirm_delete.html',
		{'product_class': product_class, 'products': products})


@staff_member_required
@permission_decorator('product.view_product')
def product_list(request):
	products = Product.objects.prefetch_related('images').order_by('-id')
	product_classes = ProductClass.objects.all()
	form = forms.ProductClassSelectorForm(
		request.POST or None, product_classes=product_classes)
	if form.is_valid():
		return redirect('dashboard:product-add',
						class_pk=form.cleaned_data['product_cls'])
	products = get_paginator_items(products, 30, request.GET.get('page'))
	ctx = {'form': form, 'products': products,
		   'product_classes': product_classes}
	user_trail(request.user.name, 'accessed the products page', 'view')
	info_logger.info('User: '+str(request.user.name)+' accessed the products page')
	return TemplateResponse(request, 'dashboard/product/list.html', ctx)
from django.views.decorators.csrf import csrf_exempt, csrf_protect
@staff_member_required
@csrf_exempt
def fetch_variants(request):
	if request.method == 'POST':
		if request.is_ajax():
			class_pk = request.POST.get("class_pk", "--")	
			product_class = get_object_or_404(ProductClass, pk=class_pk)
			create_variant = not product_class.has_variants
			product = Product()
			product.product_class = product_class
			product_form = forms.ProductForm(request.POST or None, instance=product)
			if create_variant:
				variant = ProductVariant(product=product)
				variant_form = forms.ProductVariantForm(request.POST or None,
														instance=variant,
														prefix='variant')
				variant_errors = not variant_form.is_valid()
			else:
				variant_form = None
				variant_errors = False
			ctx = {'class_pk':class_pk,'variant_form':variant_form,'product_form':product_form }
			return TemplateResponse(
		request, 'dashboard/product/attributes.html', ctx)

@staff_member_required
@permission_decorator('product.add_product')
def product_create(request):
	product_classes = ProductClass.objects.order_by('pk')
	form_classes = forms.ProductClassSelectorForm(
		request.POST or None, product_classes=product_classes)
	if form_classes.is_valid():
		class_pk=form_classes.cleaned_data['product_cls']
	else:
		class_pk= 1
	product_class = get_object_or_404(ProductClass, pk=class_pk)
	create_variant = not product_class.has_variants
	product = Product()

	product.product_class = product_class
	product_form = forms.ProductForm(request.POST or None, instance=product)
	ajax_sub = request.GET.get('ajax_subcategory')
	sub_category = request.GET.get('sub_category')
	sup= request.GET.get('supplier')
	tx = request.GET.get('tax')
	if ajax_sub:
		data = {
			'product_form': product_form,
			'sub_category':sub_category,
			'supplier':sup,
			'tax':tx
		}
		return TemplateResponse(request, 'dashboard/product/subcategory/sub_refresh.html',
								data)

	if create_variant:
		variant = ProductVariant(product=product)
		variant_form = forms.ProductVariantForm(request.POST or None,
												instance=variant,
												prefix='variant')
		variant_errors = not variant_form.is_valid()
	else:
		variant_form = None
		variant_errors = False

	if product_form.is_valid() and not variant_errors:
		product = product_form.save()
		if create_variant:
			variant.product = product
			variant_form.save()
		msg = pgettext_lazy(
			'Dashboard message', 'Added product %s') % product
		messages.success(request, msg)
		return redirect('dashboard:product-update',
						pk=product.pk)
	else:
		errors = product_form.errors
		product_cl = ProductClass()
		form = forms.ProductClassForm(request.POST or None,
									  instance=product_cl)

		ctx = {'product_form': product_form, 'variant_form': variant_form,
		   'product': product,'form_classes':form_classes, 'errors':errors,
			   'form':form, 'product_class':product_cl}
	return TemplateResponse(
		request, 'dashboard/product/product_form.html', ctx)


@staff_member_required
@permission_decorator('product.change_product')
def product_edit(request, pk):
	product = get_object_or_404(
		Product.objects.prefetch_related(
			'images', 'variants'), pk=pk)
	edit_variant = not product.product_class.has_variants
	attributes = product.product_class.variant_attributes.prefetch_related(
		'values')
	images = product.images.all()
	variants = product.variants.all()
	stock_items = Stock.objects.filter(
		variant__in=variants).select_related('variant', 'location')

	form = forms.ProductForm(request.POST or None, instance=product)
	variants_delete_form = forms.VariantBulkDeleteForm()
	stock_delete_form = forms.StockBulkDeleteForm()

	if edit_variant:
		variant = variants.first()
		variant_form = forms.ProductVariantForm(
			request.POST or None, instance=variant, prefix='variant')
		variant_errors = not variant_form.is_valid()
	else:
		variant_form = None
		variant_errors = False

	if form.is_valid() and not variant_errors:
		product = form.save()
		msg = pgettext_lazy(
			'Dashboard message', 'Updated product %s') % product
		messages.success(request, msg)
		return redirect('dashboard:product-update', pk=product.pk)
	ctx = {'attributes': attributes, 'images': images, 'product_form': form,
		   'product': product, 'stock_delete_form': stock_delete_form,
		   'stock_items': stock_items, 'variants': variants,
		   'variants_delete_form': variants_delete_form,
		   'variant_form': variant_form}
	if request.is_ajax():
		return TemplateResponse(
					request, 
					'dashboard/product/product_view.html',
					 ctx)
	return TemplateResponse(
		request, 'dashboard/product/product_form.html', ctx)


@staff_member_required
@permission_decorator('product.delete_product')
def product_delete(request, pk):
	product = get_object_or_404(Product, pk=pk)
	if request.method == 'POST':
		product.delete()
		messages.success(
			request,
			pgettext_lazy('Dashboard message', 'Deleted product %s') % product)
		return redirect('dashboard:product-list')
	return TemplateResponse(
		request, 'dashboard/product/modal_product_confirm_delete.html',
		{'product': product})

@staff_member_required
@permission_decorator('product.view_stock')
def stock_history(request,stock_pk=None):
	if request.method == 'GET':
		if stock_pk:
			instance = get_object_or_404(Stock, pk=stock_pk)
			stock_history = StockHistoryEntry.objects.filter(stock=instance).order_by('-id')
			ctx = {'stock_history':stock_history}
			return TemplateResponse(request, 'dashboard/includes/_stock_history.html', ctx)
			#return HttpResponse(len(stock_history))


@staff_member_required
def add_stock_ajax(request):
	if request.is_ajax():
		stock_pk = request.POST.get('stock_pk',None)
		quantity = request.POST.get('quantity',None)
		productName = request.POST.get('product','')
		if not quantity:
			return HttpResponse('quantity required')        
		if stock_pk:
			stock = get_object_or_404(Stock, pk=stock_pk)
		else:
			return HttpResponse('stock pk required')
		old_quantity = stock.quantity
		diff = int(quantity) - int(old_quantity)  
		crud = 'Removed' if diff < 0 else "Added"

		if crud == 'Added':
			supplier = stock.variant.product.product_supplier
			PurchaseProduct.objects.create(
							variant=stock.variant,
							stock=stock,
							cost_price=stock.cost_price,
							quantity=diff,
							supplier=supplier,
							)
		try:
			stock_list = request.session['stock_list']
			if stock_pk in stock_list:
				trail = str(productName)+' Stock '+crud+': quantity '+str(diff).replace('-','')+': Total stock '+str(quantity)              
			else:
				trail = crud+' '+str(diff)+' stock of '+str(productName)+'. Total stock '+str(quantity)                               
		except:
			stock_list = []
			stock_list.append(stock_pk)
			request.session['stock_list'] = stock_list
			trail = str(productName)+' Stock '+crud+': quantity '+str(diff).replace('-','')+': Total stock '+str(quantity)                     
	   
		user_trail(request.user.name, trail,'add')
		info_logger.info('User: '+str(request.user.name)+trail)
		stock.quantity = int(quantity)   
		stock.save()
		StockHistoryEntry.objects.create(stock=stock,comment=trail,crud=crud,user=request.user)
		message = "Stock for "+str(productName)+\
				 " updated successfully"+" current stock is "+quantity
		info_logger.error(message)
		return HttpResponse(message)


@staff_member_required
@permission_decorator('product.change_stock')
def stock_edit(request, product_pk, stock_pk=None):
	product = get_object_or_404(Product, pk=product_pk)
	if stock_pk:
		stock = get_object_or_404(Stock, pk=stock_pk)
	else:
		stock = Stock()
	form = forms.StockForm(request.POST or None, instance=stock,
						   product=product)
	if form.is_valid():
		form.save()
		
		quantity = request.POST.get('quantity')		
		cost_price = request.POST.get('cost_price')		
		invoice_number = request.POST.get('invoice_number')
		#try:
		PurchaseProduct.objects.create(
							variant=stock.variant,
							stock=stock,
							invoice_number=invoice_number,
							cost_price=cost_price,
							quantity=quantity,
							supplier=product.product_supplier,
							)
		messages.success(
			request, pgettext_lazy('Dashboard message', 'Saved stock'))
		product_url = reverse(
			'dashboard:product-update', kwargs={'pk': product_pk})
		success_url = request.POST.get('success_url', product_url)
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)			
	errors = form.errors
	ctx = {'form': form, 'product': product, 'stock': stock, 'errors':errors}
	if request.is_ajax():
		return TemplateResponse(request, 'dashboard/purchase/includes/add_stock_form.html', ctx)
	return TemplateResponse(request, 'dashboard/product/stock_form.html', ctx)


@staff_member_required
@permission_decorator('product.delete_stock')
def stock_delete(request, product_pk, stock_pk):
	product = get_object_or_404(Product, pk=product_pk)
	stock = get_object_or_404(Stock, pk=stock_pk)
	if request.method == 'POST':
		stock.delete()
		messages.success(
			request, pgettext_lazy('Dashboard message', 'Deleted stock'))
		success_url = request.POST['success_url']
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	ctx = {'product': product, 'stock': stock}
	return TemplateResponse(
		request, 'dashboard/product/stock_confirm_delete.html', ctx)


@staff_member_required
@permission_decorator('product.delete_stock')
@require_http_methods(['POST'])
def stock_bulk_delete(request, product_pk):
	product = get_object_or_404(Product, pk=product_pk)
	form = forms.StockBulkDeleteForm(request.POST)
	if form.is_valid():
		form.delete()
		success_url = request.POST['success_url']
		messages.success(
			request, pgettext_lazy('Dashboard message', 'Deleted stock'))
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	return redirect('dashboard:product-update', pk=product.pk)


@staff_member_required
@permission_decorator('product.change_productimage')
def product_image_edit(request, product_pk, img_pk=None):
	product = get_object_or_404(Product, pk=product_pk)
	if img_pk:
		product_image = get_object_or_404(product.images, pk=img_pk)
	else:
		product_image = ProductImage(product=product)
	show_variants = product.product_class.has_variants
	form = forms.ProductImageForm(request.POST or None, request.FILES or None,
								  instance=product_image)
	if form.is_valid():
		product_image = form.save()
		if img_pk:
			msg = pgettext_lazy(
				'Dashboard message',
				'Updated image %s') % product_image.image.name
		else:
			msg = pgettext_lazy(
				'Dashboard message',
				'Added image %s') % product_image.image.name
		messages.success(request, msg)
		success_url = request.POST['success_url']
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	ctx = {'form': form, 'product': product, 'product_image': product_image,
		   'show_variants': show_variants}
	return TemplateResponse(
		request, 'dashboard/product/product_image_form.html', ctx)


@staff_member_required
@permission_decorator('product.delete_productimage')
def product_image_delete(request, product_pk, img_pk):
	product = get_object_or_404(Product, pk=product_pk)
	product_image = get_object_or_404(product.images, pk=img_pk)
	if request.method == 'POST':
		product_image.delete()
		messages.success(
			request,
			pgettext_lazy(
				'Dashboard message',
				'Deleted image %s') % product_image.image.name)
		success_url = request.POST['success_url']
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	ctx = {'product': product, 'product_image': product_image}
	return TemplateResponse(
		request,
		'dashboard/product/modal_product_image_confirm_delete.html', ctx)


@staff_member_required
@permission_decorator('product.change_productvariants')
def variant_edit(request, product_pk, variant_pk=None):
	product = get_object_or_404(Product.objects.all(),
								pk=product_pk)
	form_initial = {}
	if variant_pk:
		variant = get_object_or_404(product.variants.all(),
									pk=variant_pk)
	else:
		variant = ProductVariant(product=product)
	form = forms.ProductVariantForm(request.POST or None, instance=variant,
									initial=form_initial)
	attribute_form = forms.VariantAttributeForm(request.POST or None,
												instance=variant)
	if all([form.is_valid(), attribute_form.is_valid()]):
		form.save()
		attribute_form.save()
		if variant_pk:
			msg = pgettext_lazy(
				'Dashboard message',
				'Updated variant %s') % variant.name
		else:
			msg = pgettext_lazy(
				'Dashboard message',
				'Added variant %s') % variant.name
		messages.success(request, msg)
		success_url = request.POST['success_url']
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	errors = attribute_form.errors
	form_errors = form.errors
	ctx = {'attribute_form': attribute_form, 'form': form, 'product': product,
		   'variant': variant,'errors':errors,'form_errors':form_errors}
	return TemplateResponse(
		request, 'dashboard/product/variant_form.html', ctx)


@staff_member_required
@permission_decorator('product.delete_productvariants')
def variant_delete(request, product_pk, variant_pk):
	product = get_object_or_404(Product, pk=product_pk)
	variant = get_object_or_404(product.variants, pk=variant_pk)
	is_only_variant = product.variants.count() == 1
	if request.method == 'POST':
		variant.delete()
		messages.success(
			request,
			pgettext_lazy(
				'Dashboard message', 'Deleted variant %s') % variant.name)
		success_url = request.POST['success_url']
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	ctx = {'is_only_variant': is_only_variant, 'product': product,
		   'variant': variant}
	return TemplateResponse(
		request,
		'dashboard/product/modal_product_variant_confirm_delete.html', ctx)


@staff_member_required
@permission_decorator('product.delete_productvariants')
@require_http_methods(['POST'])
def variants_bulk_delete(request, product_pk):
	product = get_object_or_404(Product, pk=product_pk)
	form = forms.VariantBulkDeleteForm(request.POST)
	if form.is_valid():
		form.delete()
		success_url = request.POST['success_url']
		messages.success(
			request,
			pgettext_lazy('Dashboard message', 'Deleted variants'))
		if is_safe_url(success_url, request.get_host()):
			return redirect(success_url)
	return redirect('dashboard:product-update', pk=product.pk)

@staff_member_required
def view_attr(request):
	try:
		queryset_list = [
			(attribute.pk, attribute.name, attribute.values.all())
			for attribute in ProductAttribute.objects.prefetch_related('values').order_by('-id')]

		page = request.GET.get('page', 1)
		paginator = Paginator(queryset_list, 10)
		try:
			queryset_list = paginator.page(page)
		except PageNotAnInteger:
			queryset_list = paginator.page(1)
		except InvalidPage:
			queryset_list = paginator.page(1)
		except EmptyPage:
			queryset_list = paginator.page(paginator.num_pages)
		product_results = queryset_list
		user_trail(request.user.name, 'accessed the roles page','view')
		info_logger.info('User: '+str(request.user.name)+' accessed the roles page page')

		data ={
			'attributes': product_results,
			'totalp':paginator.num_pages
			   }
		if request.GET.get('initial'):
			return HttpResponse(paginator.num_pages)
		else:
			return TemplateResponse(request, 'dashboard/product/attributes/pagination/view.html', data)
	except TypeError as e:
		error_logger.error(e)
		return HttpResponse('error accessing users')

def paginate_attr(request):
	page = int(request.GET.get('page', 1))
	list_sz = request.GET.get('size')
	p2_sz = request.GET.get('psize')
	select_sz = request.GET.get('select_size')

	try:
		queryset_list = [
			(attribute.pk, attribute.name, attribute.values.all())
			for attribute in ProductAttribute.objects.prefetch_related('values').order_by('-id')]

		if list_sz:
			paginator = Paginator(queryset_list, int(list_sz))
			queryset_list = paginator.page(page)
			product_results = queryset_list
			data = {
				'attributes': product_results,
				'pn': paginator.num_pages,
				'sz': list_sz,
				'gid': 0
			}
			return TemplateResponse(request, 'dashboard/product/attributes/pagination/p2.html', data)
		else:
			paginator = Paginator(queryset_list, 10)
			if p2_sz:
				paginator = Paginator(queryset_list, int(p2_sz))
			queryset_list = paginator.page(page)
			product_results = queryset_list
			data = {
				'attributes': product_results,
			}
			return TemplateResponse(request, 'dashboard/product/attributes/pagination/paginate.html', data)

		try:
			queryset_list = paginator.page(page)
		except PageNotAnInteger:
			queryset_list = paginator.page(1)
		except InvalidPage:
			queryset_list = paginator.page(1)
		except EmptyPage:
			queryset_list = paginator.page(paginator.num_pages)
		product_results = queryset_list
		return TemplateResponse(request, 'dashboard/product/attributes/pagination/paginate.html', {'attributes': product_results})
	except Exception, e:
		return  HttpResponse()


# @staff_member_required
# @permission_decorator('product.view_productattribute')
# def attribute_list(request):
# 	attributes = [
# 		(attribute.pk, attribute.name, attribute.values.all())
# 		for attribute in ProductAttribute.objects.prefetch_related('values').order_by('-id')]
# 	ctx = {'attributes': attributes}
# 	return TemplateResponse(request, 'dashboard/product/attributes/list.html',
# 							ctx)

@staff_member_required
@permission_decorator('product.add_productattribute')
def attribute_add_modal(request):
	attribute_name = request.POST.get("attribute")
	values = request.POST.getlist("values")

	try:
		ProductAttribute.objects.create(slug=attribute_name, name=attribute_name);
		last_attribute = ProductAttribute.objects.latest('id')

		for i in values:
			p = AttributeChoiceValue.objects.create(attribute=last_attribute,
													slug = i, name = i)
			p.save()

		attributes = ProductAttribute.objects.all()
		product_cl = ProductClass()
		form = forms.ProductClassForm(request.POST or None,
									  instance=product_cl)
		ctx = {'attributes': attributes, 'form':form}

		return TemplateResponse(request, 'dashboard/product/attributes/select.html', ctx)
	except Exception, e:
		return HttpResponse(e)

@staff_member_required
@permission_decorator('product.add_productattribute')
def attribute_add(request,pk=None):
	if request.method == 'POST':
		if pk:
			attribute = get_object_or_404(ProductAttribute, pk=pk)
			name = request.POST.get("value")
			if name != '':
				AttributeChoiceValue.objects.create(attribute=attribute,slug=name,name=name);        
				last_id = ProductAttribute.objects.latest('id')
				choices = AttributeChoiceValue.objects.filter(attribute=attribute)
				ctx = {'choices':choices}
				return TemplateResponse(request, 'dashboard/product/attributes/add_value.html',
							ctx)
		name = request.POST.get("name")
		if name != '':
			ProductAttribute.objects.create(slug=name,name=name);        
			last_id = ProductAttribute.objects.latest('id')
			return HttpResponse(last_id.pk)
	elif request.method == 'GET':
			ctx = {}
			if pk:
				product_class = get_object_or_404(ProductClass, pk=pk)
				attributes = product_class.product_attributes.all()
				ctx = {'product_type':product_class,'attributes':attributes}			

			return TemplateResponse(request,'dashboard/product/attributes/_edit_values.html',ctx)
	return HttpResponse('bad request')

@staff_member_required
@permission_decorator('product.change_productattribute')
def attribute_edit(request, pk=None):
	if pk:
		attribute = get_object_or_404(ProductAttribute, pk=pk)
	else:
		attribute = ProductAttribute()
	form = forms.ProductAttributeForm(request.POST or None, instance=attribute)
	formset = forms.AttributeChoiceValueFormset(request.POST or None,
												request.FILES or None,
												instance=attribute)
	if all([form.is_valid(), formset.is_valid()]):
		attribute = form.save()
		formset.save()
		msg = pgettext_lazy(
			'Dashboard message', 'Updated attribute') if pk else pgettext_lazy(
				'Dashboard message', 'Added attribute')
		messages.success(request, msg)
		return redirect('dashboard:product-attribute-update', pk=attribute.pk)
	ctx = {'attribute': attribute, 'form': form, 'formset': formset}
	return TemplateResponse(request, 'dashboard/product/attributes/form.html',
							ctx)


@staff_member_required
@permission_decorator('product.delete_productattribute')
def attribute_delete(request, pk):
	attribute = get_object_or_404(ProductAttribute, pk=pk)
	if request.method == 'POST':
		attribute.delete()
		messages.success(
			request,
			pgettext_lazy(
				'Dashboard message',
				'Deleted attribute %s') % (attribute.name,))
		return redirect('dashboard:product-attributes')
	ctx = {'attribute': attribute}
	return TemplateResponse(
		request, 'dashboard/product/attributes/modal_confirm_delete.html', ctx)


@staff_member_required
@permission_decorator('product.view_stocklocation')
def stock_location_list(request):
	stock_locations = StockLocation.objects.all()
	ctx = {'locations': stock_locations}
	return TemplateResponse(
		request, 'dashboard/product/stock_locations/list.html', ctx)


@staff_member_required
@permission_decorator('product.change_stocklocation')
def stock_location_edit(request, location_pk=None):
	if location_pk:
		location = get_object_or_404(StockLocation, pk=location_pk)
	else:
		location = StockLocation()
	form = forms.StockLocationForm(request.POST or None, instance=location)
	if form.is_valid():
		form.save()
		msg = pgettext_lazy(
			'Dashboard message for stock location',
			'Updated location') if location_pk else pgettext_lazy(
				'Dashboard message for stock location', 'Added location')
		messages.success(request, msg)
		return redirect('dashboard:product-stock-location-list')
	ctx = {'form': form, 'location': location}
	return TemplateResponse(
		request, 'dashboard/product/stock_locations/form.html', ctx)


@staff_member_required
@permission_decorator('product.delete_stocklocation')
def stock_location_delete(request, location_pk):
	location = get_object_or_404(StockLocation, pk=location_pk)
	stock_count = location.stock_set.count()
	if request.method == 'POST':
		location.delete()
		messages.success(
			request, pgettext_lazy(
				'Dashboard message for stock location',
				'Deleted location %s') % location)
		return redirect('dashboard:product-stock-location-list')
	ctx = {'location': location, 'stock_count': stock_count}
	return TemplateResponse(
		request, 'dashboard/product/stock_locations/modal_confirm_delete.html',
		ctx)
from .forms import ProductTaxForm

@staff_member_required
@permission_decorator('product.view_producttax')
def tax_list(request):
	form = ProductTaxForm(request)
	ctx = {'tax': ProductTax.objects.all()}
	return TemplateResponse(
		request, 'dashboard/product/tax_list.html',
		ctx)

@staff_member_required
def refresh_producttype(request):
	product = Product()
	class_pk = 1
	product_class = get_object_or_404(ProductClass, pk=class_pk)
	product.product_class = product_class
	product_form = forms.ProductForm(request.POST or None, instance=product)
	ctx = {'product_form':product_form,'added':'added' }
	return TemplateResponse(
	request, 'dashboard/includes/_producttype_success.html',
	ctx)

@staff_member_required
@csrf_exempt
def tax_add_ajax(request):
	if request.method == 'POST':
		if request.is_ajax():
			tax_id = request.POST.get("tax_id")
			if tax_id: 
				product_tax = ProductTax()
				tax = ProductTax.objects.filter(pk=tax_id)
				for t in tax:
					tax = t.tax
				return HttpResponse(tax)
			product_tax = ProductTax()
			formadd = ProductTaxForm(request.POST or None,
								  instance=product_tax)
			if formadd.is_valid():
				tax = formadd.save()
				msg = pgettext_lazy(
					'Dashboard message', 'Added Tax') 
				messages.success(request, msg)
				product = Product()
				class_pk = 1
				product_class = get_object_or_404(ProductClass, pk=class_pk)
				product.product_class = product_class
				product_form = forms.ProductForm(request.POST or None, instance=product)
				ctx = {'product_form':product_form,'added':'added' }
				return TemplateResponse(
				request, 'dashboard/includes/_tax_success.html',
				ctx)
			else:
				ctx = {'tax':ProductTax.objects.all(),'formadd':formadd,'errors':formadd.errors}
		   
			return TemplateResponse(
				request, 'dashboard/includes/_tax_ajax_form.html',
				ctx)

@staff_member_required
@permission_decorator('product.add_producttax')
def tax_add(request):
	product_tax = ProductTax()
	formadd = ProductTaxForm(request.POST or None,
								  instance=product_tax)
	if formadd.is_valid():
		tax = formadd.save()
		msg = pgettext_lazy(
			'Dashboard message', 'Added Tax') 
		messages.success(request, msg)
		return redirect('dashboard:tax-list')
	else:
		ctx = {'tax':ProductTax.objects.all(),'form':formadd,'errors':formadd.errors}
   
	return TemplateResponse(
		request, 'dashboard/product/tax_form.html',
		ctx)

@staff_member_required
@permission_decorator('product.change_producttax')
def tax_edit(request, pk=None):
	if pk:
		instance = get_object_or_404(ProductTax, pk=pk)
	else:
		instance = ProductTax()
	form = forms.ProductTaxForm(
		request.POST or None, instance=instance)
	if form.is_valid():
		instance = form.save()
		msg = pgettext_lazy(
			'Product (Tax) message', 'Updated tax') if pk else pgettext_lazy(
				'Sale (tax) message', 'Added tax')
		messages.success(request, msg)
		return redirect('dashboard:tax-list')
	ctx = {'sale': instance, 'form': form,'tax_instance':instance}
	return TemplateResponse(request, 'dashboard/product/tax_form.html', ctx)

@staff_member_required
@permission_decorator('product.delete_producttax')
def tax_delete(request, pk):
	instance = get_object_or_404(ProductTax, pk=pk)
	if request.method == 'POST':
		instance.delete()
		messages.success(
			request,
			pgettext_lazy('Tax message', 'Deleted Tax %s') % (instance.tax_name,))
		return redirect('dashboard:tax-list')
	ctx = {'instance': instance}
	return TemplateResponse(
		request, 'dashboard/product/tax_list.html', ctx)

# purchase views
@staff_member_required
def purchase_list(request):
	form = forms.StockPurchaseForm(request)
	ctx = {'stock': Stock.objects.all()}
	return TemplateResponse(
		request, 'dashboard/purchase/purchase_list.html',
		ctx)

@staff_member_required
def search_product(request):
	if request.method == 'POST':
		if request.is_ajax():
			search  = request.POST.get("search_product", "--") 
			product = Product()
			products_count = len(Product.objects.all())
			product_results = Product.objects.filter(
						Q(name__icontains=search)|
						Q(variants__sku__icontains=search)|
						Q(categories__name__icontains=search)
						)
			search_count = len(product_results)
			ctx = {'products_count': products_count,'product_results': product_results,'search_count':search_count}
			return TemplateResponse(
		request, 'dashboard/includes/product_search_results.html',
		ctx)

@staff_member_required
def stock_pages(request):
	queryset_list = ProductVariant.objects.all()
	size = request.GET.get('size',10)
	page = request.GET.get('page',1)
	search = str(request.GET.get('search_text',''))
	if search != '' and search != None:
		queryset_list = ProductVariant.objects.filter(
			Q(sku__icontains=search) |
			Q(product__name__icontains=search)
			).order_by('-id') 
	paginator = Paginator(queryset_list,int(size)) # Show 10 contacts per page
	
	try:
		queryset = paginator.page(int(page))
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		queryset = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		queryset = paginator.page(paginator.num_pages)
	return HttpResponse(paginator.num_pages)

@staff_member_required
def stocks(request):
	try:
		product_results = ProductVariant.objects.all().order_by('-id')		
		page = request.GET.get('page', 1)
		categories = Category.objects.all()
		paginator = Paginator(product_results, 10)
		try:
			product_results = paginator.page(page)
		except PageNotAnInteger:
			product_results = paginator.page(1)
		except InvalidPage:
			product_results = paginator.page(1)
		except EmptyPage:
			product_results = paginator.page(paginator.num_pages)
		if request.GET.get('initial'):
			return HttpResponse(paginator.num_pages)
		else:
			return TemplateResponse(request, 'dashboard/purchase/purchase_list.html', {'product_results':product_results,'categories':categories})
	except TypeError as e:
		error_logger.error(e)
		return HttpResponse('error accessing users')

@staff_member_required
def stock_paginate(request):
	page = int(request.GET.get('page', 1))
	list_sz = request.GET.get('size')
	p2_sz = request.GET.get('psize')
	select_sz = request.GET.get('select_size')
	if request.GET.get('gid'):
		product_results = ProductVariant.objects.filter(product__categories=request.GET.get('gid'))
		if p2_sz:
			paginator = Paginator(product_results, int(p2_sz))
			product_results = paginator.page(page)
			return TemplateResponse(request,'dashboard/purchase/paginate.html',{'product_results':product_results})

		paginator = Paginator(product_results, 10)
		product_results = paginator.page(page)
		return TemplateResponse(request,'dashboard/purchase/p2.html',{'product_results':product_results, 'pn':paginator.num_pages,'sz':10,'gid':request.GET.get('gid')})

	else:
		product_results = ProductVariant.objects.all().order_by('-id')
		if list_sz:
			paginator = Paginator(product_results, int(list_sz))
			product_results = paginator.page(page)
			print product_results
			print 'sdflsdjflsdjf'
			return TemplateResponse(request,'dashboard/purchase/p2.html',{'product_results':product_results, 'pn':paginator.num_pages,'sz':list_sz, 'gid':0})
		else:
			paginator = Paginator(product_results, 10)
		if p2_sz:
			paginator = Paginator(product_results, int(p2_sz))
			product_results = paginator.page(page)
			return TemplateResponse(request,'dashboard/purchase/paginate.html',{'product_results':product_results})

		try:
			product_results = paginator.page(page)
		except PageNotAnInteger:
			product_results = paginator.page(1)
		except InvalidPage:
			groups = paginator.page(1)
		except EmptyPage:
			product_results = paginator.page(paginator.num_pages)
		return TemplateResponse(request,'dashboard/purchase/paginate.html',{'product_results':product_results})


@staff_member_required
def stock_search( request ):
	
	if request.is_ajax():
		page = request.GET.get('page', 1)
		list_sz = request.GET.get('size',10)
		p2_sz = request.GET.get('psize')
		q = request.GET.get( 'q' )
		if list_sz is None:
			sz = 10
		else:
			sz = list_sz
		if q is not None:            
			product_results = ProductVariant.objects.filter( 
				Q(sku__icontains=q) |
				Q(product__name__icontains=q)).order_by('-id')
			paginator = Paginator(product_results, 10)
			try:
				product_results = paginator.page(page)
			except PageNotAnInteger:
				product_results = paginator.page(1)
			except InvalidPage:
				product_results = paginator.page(1)
			except EmptyPage:
				product_results = paginator.page(paginator.num_pages)
			if p2_sz:
				product_results = paginator.page(page)
				return TemplateResponse(request,'dashboard/purchase/paginate.html',{'product_results':product_results})

			return TemplateResponse(request, 'dashboard/purchase/search.html', {'product_results':product_results, 'pn':paginator.num_pages,'sz':sz,'q':q})

@staff_member_required
def stock_filter(request):
	queryset_list = ProductVariant.objects.all()
	#paginator = Paginator(queryset_list, 10)
	page = request.GET.get('page',1)
	size = request.GET.get('size',10)
	search = request.GET.get('search_text','')
	if search != '' and search != None:
		queryset_list = ProductVariant.objects.filter(
			Q(sku__icontains=search) |
			Q(product__name__icontains=search)
			).order_by('-id')            
	paginator = Paginator(queryset_list, int(size))
	products_count = len(queryset_list)
	try:
		queryset = paginator.page(int(page))
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		queryset = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		queryset = paginator.page(paginator.num_pages)
	product_results = queryset    
	ctx = {'pn':paginator.num_pages,'products_count': products_count,'product_results': product_results,'search_count':len(product_results)}
	return TemplateResponse(
	request, 'dashboard/includes/sku_search_results.html',
	ctx)

@staff_member_required
@permission_decorator('product.view_product')
def product_pages(request):
	queryset_list = Product.objects.all()
	size = request.GET.get('size',10)
	page = request.GET.get('page',1)
	search = str(request.GET.get('search_text',''))
	if search != '' and search != None:
		queryset_list = Product.objects.filter(
			Q(sku__icontains=search) |
			Q(product__name__icontains=search)
			).order_by('-id').distinct()
	paginator = Paginator(queryset_list,int(size)) # Show 10 contacts per page
	
	try:
		queryset = paginator.page(int(page))
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		queryset = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		queryset = paginator.page(paginator.num_pages)
	return HttpResponse(paginator.num_pages)

@staff_member_required
def product_filter(request):
	queryset_list = Product.objects.all()
	#paginator = Paginator(queryset_list, 10)
	page = request.GET.get('page',1)
	size = request.GET.get('size',10)
	search = request.GET.get('search_text','')
	if search != '' and search != None:
		queryset_list = Product.objects.filter(
		   Q(name__icontains=search)|
		   Q(variants__sku__icontains=search)|
		   Q(categories__name__icontains=search)
			).order_by('-id').distinct()            
	paginator = Paginator(queryset_list, int(size))
	products_count = len(queryset_list)
	try:
		queryset = paginator.page(int(page))
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		queryset = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		queryset = paginator.page(paginator.num_pages)
	product_results = queryset    
	ctx = {'products_count': products_count,'product_results': product_results,'search_count':len(product_results)}
	return TemplateResponse(
	request, 'dashboard/includes/product_search_results.html',
	ctx)
	

@staff_member_required
def search_sku(request):
	if request.method == 'POST':
		search = request.POST.get("search_product", "--")
	if request.method == 'GET':
		search = request.GET.get('search_product')
	if request.is_ajax():                
		product = Product()
		products_count = len(ProductVariant.objects.all())
		product_results = ProductVariant.objects.filter(
			Q(sku__icontains=search) |
			Q(product__name__icontains=search)
			)            
		search_count = len(product_results)
		ctx = {'products_count': products_count,'product_results': product_results,'search_count':search_count}
		return TemplateResponse(
	request, 'dashboard/includes/sku_search_results.html',
	ctx)
	

@staff_member_required
def search_productclass(request):
	if request.method == 'POST':
		if request.is_ajax():
			search  = request.POST.get("search_product", "--") 
			product_class = ProductClass()
			productClass_count = len(ProductClass.objects.all())
			productClass_results = ProductClass.objects.filter(
				name__icontains=search                
				).all().prefetch_related('product_attributes', 'variant_attributes')            
			productClass_results = get_paginator_items(productClass_results, 30, request.GET.get('page'))
			productClass_results.object_list = [
				(pc.pk, pc.name, pc.has_variants, pc.product_attributes.all(),
					pc.variant_attributes.all())
				for pc in productClass_results.object_list]
			search_count = len(productClass_results)
			ctx = {'productClass_count': productClass_count,'productClass_results': productClass_results,'search_count':search_count}
			return TemplateResponse(
		request, 'dashboard/includes/class_search_results.html',
		ctx)
@staff_member_required
def search_attribute(request):
	if request.method == 'POST':
		if request.is_ajax():
			search  = request.POST.get("search_product", "--") 
			attributes = [
				(attribute.pk, attribute.name, attribute.values.all())
			for attribute in ProductAttribute.objects.filter(name__icontains=search).prefetch_related('values')]
	
			productAttribute_count = len(ProductAttribute.objects.all())
			productAttribute_results = ProductAttribute.objects.filter(name__icontains=search)            
			search_count = len(attributes)
			ctx = {
			'productAttribute_count': productAttribute_count,
			'attributes': attributes,
			'search_count':search_count
			}
			return TemplateResponse(
		request, 'dashboard/includes/attribute_search_results.html',
		ctx)

@staff_member_required
def search_attribute(request):
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
			queryset_list = [
				(attribute.pk, attribute.name, attribute.values.all())
			for attribute in ProductAttribute.objects.filter(name__icontains=q).prefetch_related('values')]
			paginator = Paginator(queryset_list, 10)

			try:
				queryset_list = paginator.page(page)
			except PageNotAnInteger:
				queryset_list = paginator.page(1)
			except InvalidPage:
				queryset_list = paginator.page(1)
			except EmptyPage:
				queryset_list = paginator.page(paginator.num_pages)
			product_results = queryset_list
			if p2_sz:
				queryset_list = paginator.page(page)
				return TemplateResponse(request, 'dashboard/product/attributes/pagination/paginate.html', {'attributes': product_results})

			return TemplateResponse(request, 'dashboard/product/attributes/pagination/search.html',
									{'attributes':product_results, 'pn': paginator.num_pages, 'sz': sz, 'q': q})