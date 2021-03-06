from __future__ import unicode_literals

from decimal import Decimal
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import pgettext_lazy
from django_countries.fields import Country, CountryField
from ..search import index
#from ..sale.models import Sales


class AddressBookManager(models.Manager):

    def as_data(self, address):
        data = model_to_dict(addressbook, exclude=['id', 'user'])
        if isinstance(data['country'], Country):
            data['country'] = data['country'].code
        return data

    def are_identical(self, addr1, addr2):
        data1 = self.as_data(addr1)
        data2 = self.as_data(addr2)
        return data1 == data2

    def store_address(self, user, address):
        data = self.as_data(address)
        address, dummy_created = user.addresses.get_or_create(**data)
        return address


@python_2_unicode_compatible
class AddressBook(models.Model):
    first_name = models.CharField(
        pgettext_lazy('AddressBook field', 'given name'),
        max_length=256, blank=True)
    last_name = models.CharField(
        pgettext_lazy('AddressBook field', 'family name'),
        max_length=256, blank=True)
    company_name = models.CharField(
        pgettext_lazy('AddressBook field', 'company or organization'),
        max_length=256, blank=True)
    street_address_1 = models.CharField(
        pgettext_lazy('AddressBook field', 'address'),
        max_length=256, blank=True)
    street_address_2 = models.CharField(
        pgettext_lazy('AddressBook field', 'address'),
        max_length=256, blank=True)
    city = models.CharField(
        pgettext_lazy('AddressBook field', 'city'),
        max_length=256, blank=True)
    city_area = models.CharField(
        pgettext_lazy('AddressBook field', 'district'),
        max_length=128, blank=True)
    postal_code = models.CharField(
        pgettext_lazy('AddressBook field', 'postal code'),
        max_length=20, blank=True)
    country = CountryField(
        pgettext_lazy('AddressBook field', 'country'))
    country_area = models.CharField(
        pgettext_lazy('AddressBook field', 'state or province'),
        max_length=128, blank=True)
    phone = models.CharField(
        pgettext_lazy('AddressBook field', 'phone number'),
        max_length=30, blank=True)
    objects = AddressBookManager()

    @property
    def full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    class Meta:
        verbose_name = pgettext_lazy('AddressBook model', 'address book')
        verbose_name_plural = pgettext_lazy('AddressBook model', 'address books')

    def __str__(self):
        if self.company_name:
            return '%s - %s' % (self.company_name, self.full_name)
        return self.full_name

    def __repr__(self):
        return (
            'AddressBook(first_name=%r, last_name=%r, company_name=%r, '
            'street_address_1=%r, street_address_2=%r, city=%r, '
            'postal_code=%r, country=%r, country_area=%r, phone=%r)' % (
                self.first_name, self.last_name, self.company_name,
                self.street_address_1, self.street_address_2, self.city,
                self.postal_code, self.country, self.country_area,
                self.phone))


class CustomerManager(BaseUserManager):

    def create_customer(self, email, password=None,
                    is_active=True, username='', **extra_fields):
        'Creates a User with the given username, email and password'
        email = CustomerManager.normalize_email(email)
        customer = self.model(email=email, is_active=is_active,
                           **extra_fields)
        if password:
            customer.set_password(password)
        customer.save()
        return customer
    

class Customer(models.Model):
    email = models.EmailField(pgettext_lazy('Customer field', 'email'), unique=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    addresses = models.ManyToManyField(
        AddressBook, blank=True,
        verbose_name=pgettext_lazy('Customer field', 'addresses'))   
    is_active = models.BooleanField(
        pgettext_lazy('Customer field', 'active'),
        default=True)
    loyalty_points = models.DecimalField(
        pgettext_lazy('Customer field', 'loyalty points'), default=Decimal(0), max_digits=100, decimal_places=2)    
    nid = models.CharField(max_length=100, null=True,blank=True)
    mobile = models.CharField(max_length=100, null=True, blank=True)
    image = models.FileField(upload_to='employee', blank=True, null=True)
    date_joined = models.DateTimeField(
        pgettext_lazy('Customer field', 'date joined'),
        default=timezone.now, editable=False)
    default_shipping_address = models.ForeignKey(
        AddressBook, related_name='+', null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=pgettext_lazy('Customer field', 'default shipping address'))
    default_billing_address = models.ForeignKey(
        AddressBook, related_name='+', null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=pgettext_lazy('Customer field', 'default billing address'))

    USERNAME_FIELD = 'email'

    objects = CustomerManager()

    search_fields = [
        index.SearchField('email')]

    class Meta:
        verbose_name = pgettext_lazy('Customer model', 'customer')
        verbose_name_plural = pgettext_lazy('Customer model', 'customers')

    def __str__(self):
        return self.name

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email
    def get_sales(self):
        return len(self.customers.all())
