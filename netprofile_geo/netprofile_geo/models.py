#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (
	unicode_literals,
	print_function,
	absolute_import,
	division
)

__all__ = [
	'City',
	'District',
	'Street',
	'House',
	'Place',
	'HouseGroup',
	'HouseGroupMapping'
]

from sqlalchemy import (
	Column,
	ForeignKey,
	Index,
	Sequence,
	Unicode,
	UnicodeText,
	text
)

from sqlalchemy.orm import (
	backref,
	contains_eager,
	relationship
)

from sqlalchemy.ext.associationproxy import (
	association_proxy
)

#from colanderalchemy import (
#	Column,
#	relationship
#)

from netprofile.db.connection import (
	Base,
	DBSession
)
from netprofile.db.fields import (
	UInt8,
	UInt16,
	UInt32
)
from netprofile.ext.filters import (
	CheckboxGroupFilter
)
from netprofile.ext.wizards import (
	SimpleWizard,
	Step,
	Wizard
)
from netprofile.db.ddl import Comment
from netprofile.db.util import populate_related_list

from netprofile_geo.filters import AddressFilter

from pyramid.threadlocal import get_current_request
from pyramid.i18n import (
	TranslationStringFactory,
	get_localizer
)

_ = TranslationStringFactory('netprofile_geo')

class City(Base):
	"""
	City object.
	"""
	__tablename__ = 'addr_cities'
	__table_args__ = (
		Comment('Cities'),
		Index('addr_cities_u_name', 'name', unique=True),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'cap_menu'      : 'BASE_GEO',
				'cap_read'      : 'GEO_LIST',
				'cap_create'    : 'GEO_CREATE',
				'cap_edit'      : 'GEO_EDIT',
				'cap_delete'    : 'GEO_DELETE',

				'show_in_menu'  : 'admin',
				'menu_name'     : _('Cities'),
				'menu_order'    : 40,
				'default_sort'  : ({ 'property': 'name' ,'direction': 'ASC' },),
				'grid_view'     : ('name', 'prefix'),
				'easy_search'   : ('name',),
				'detail_pane'   : ('netprofile_core.views', 'dpane_simple'),

				'create_wizard' : SimpleWizard(title=_('Add new city'))
			}
		}
	)

	id = Column(
		'cityid',
		UInt32(),
		Sequence('cityid_seq'),
		Comment('City ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	name = Column(
		Unicode(255),
		Comment('City name'),
		nullable=False,
		info={
			'header_string' : _('Name')
		}
	)
	prefix = Column(
		Unicode(32),
		Comment('Contract prefix'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Prefix')
		}
	)

	districts = relationship(
		'District',
		backref=backref('city', innerjoin=True),
		cascade='all, delete-orphan',
		passive_deletes=True
	)

	def __str__(self):
		return '%s' % str(self.name)

class District(Base):
	"""
	City district object.
	"""
	__tablename__ = 'addr_districts'
	__table_args__ = (
		Comment('Districts'),
		Index('addr_districts_u_name', 'name', unique=True),
		Index('addr_districts_i_cityid', 'cityid'),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'cap_menu'      : 'BASE_GEO',
				'cap_read'      : 'GEO_LIST',
				'cap_create'    : 'GEO_CREATE',
				'cap_edit'      : 'GEO_EDIT',
				'cap_delete'    : 'GEO_DELETE',

				'show_in_menu'  : 'admin',
				'menu_name'     : _('Districts'),
				'menu_order'    : 50,
				'default_sort'  : ({ 'property': 'name' ,'direction': 'ASC' },),
				'grid_view'     : ('city', 'name', 'prefix'),
				'easy_search'   : ('name',),
				'detail_pane'   : ('netprofile_core.views', 'dpane_simple'),

				'create_wizard' : SimpleWizard(title=_('Add new district'))
			}
		}
	)

	id = Column(
		'districtid',
		UInt32(),
		Sequence('districtid_seq'),
		Comment('District ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	city_id = Column(
		'cityid',
		UInt32(),
		ForeignKey('addr_cities.cityid', name='addr_districts_fk_cityid', ondelete='CASCADE', onupdate='CASCADE'),
		Comment('City ID'),
		nullable=False,
		info={
			'header_string' : _('City'),
			'filter_type'   : 'list'
		}
	)
	name = Column(
		Unicode(255),
		Comment('District name'),
		nullable=False,
		info={
			'header_string' : _('Name')
		}
	)
	prefix = Column(
		Unicode(32),
		Comment('Contract prefix'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Prefix')
		}
	)

	streets = relationship(
		'Street',
		backref=backref('district', innerjoin=True),
		cascade='all, delete-orphan',
		passive_deletes=True
	)

	def __str__(self):
		return '%s' % str(self.name)

class Street(Base):
	"""
	Street object.
	"""
	__tablename__ = 'addr_streets'
	__table_args__ = (
		Comment('Streets'),
		Index('addr_streets_u_street', 'prefix', 'suffix', 'name', unique=True),
		Index('addr_streets_u_name', 'name', unique=True),
		Index('addr_streets_i_districtid', 'districtid'),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'cap_menu'      : 'BASE_GEO',
				'cap_read'      : 'GEO_LIST',
				'cap_create'    : 'GEO_CREATE',
				'cap_edit'      : 'GEO_EDIT',
				'cap_delete'    : 'GEO_DELETE',

				'show_in_menu'  : 'admin',
				'menu_name'     : _('Streets'),
				'menu_order'    : 60,
				'default_sort'  : ({ 'property': 'name' ,'direction': 'ASC' },),
				'grid_view'     : ('district', 'name', 'prefix', 'suffix'),
				'easy_search'   : ('name',),
				'detail_pane'   : ('netprofile_core.views', 'dpane_simple'),

				'create_wizard' : SimpleWizard(title=_('Add new street'))
			}
		}
	)

	id = Column(
		'streetid',
		UInt32(),
		Sequence('streetid_seq'),
		Comment('Street ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	district_id = Column(
		'districtid',
		UInt32(),
		ForeignKey('addr_districts.districtid', name='addr_streets_fk_districtid', ondelete='CASCADE', onupdate='CASCADE'),
		Comment('District ID'),
		nullable=False,
		info={
			'header_string' : _('District'),
			'filter_type'   : 'list'
		}
	)
	name = Column(
		Unicode(255),
		Comment('Street name'),
		nullable=False,
		info={
			'header_string' : _('Name')
		}
	)
	prefix = Column(
		Unicode(8),
		Comment('Street name prefix'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Prefix')
		}
	)
	suffix = Column(
		Unicode(8),
		Comment('Street name suffix'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Suffix')
		}
	)

	houses = relationship(
		'House',
		backref=backref('street', innerjoin=True),
		cascade='all, delete-orphan',
		passive_deletes=True
	)

	@classmethod
	def __augment_query__(cls, sess, query, params):
		flt = {}
		if '__filter' in params:
			flt.update(params['__filter'])
		if '__ffilter' in params:
			flt.update(params['__ffilter'])
		if ('cityid' in flt) and ('eq' in flt['cityid']):
			val = int(flt['cityid']['eq'])
			if val > 0:
				query = query.join(Street.district).options(contains_eager(Street.district)).filter(District.city_id == val)
		return query

	def __str__(self):
		l = []
		if self.prefix:
			l.append(self.prefix)
		l.append(self.name)
		if self.suffix:
			l.append(self.suffix)
		return ' '.join(l)

class House(Base):
	"""
	House object. Used for anything with an exact address.
	"""

	@classmethod
	def _filter_hgroup(cls, query, value):
		if not isinstance(value, list):
			value = [value]
		return query.join(HouseGroupMapping).filter(HouseGroupMapping.group_id.in_(value))

	@classmethod
	def _filter_address(cls, query, value):
		if not isinstance(value, dict):
			return query
		if 'districtid' in value:
			val = int(value['districtid'])
			if val > 0:
				query = query.filter(Street.district_id == val)
		elif 'cityid' in value:
			val = int(value['cityid'])
			if val > 0:
				sess = DBSession()
				sq = sess.query(District).filter(District.city_id == val)
				val = [d.id for d in sq]
				if len(val) > 0:
					query = query.filter(Street.district_id.in_(val))
				else:
					query = query.filter(False)
		return query

	__tablename__ = 'addr_houses'
	__table_args__ = (
		Comment('Houses'),
		Index('addr_houses_u_house', 'streetid', 'number', 'num_slash', 'num_suffix', 'building', unique=True),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'cap_menu'     : 'BASE_GEO',
				'cap_read'     : 'GEO_LIST',
				'cap_create'   : 'GEO_CREATE',
				'cap_edit'     : 'GEO_EDIT',
				'cap_delete'   : 'GEO_DELETE',

				'show_in_menu' : 'admin',
				'menu_name'    : _('Houses'),
				'menu_order'   : 70,
				'default_sort' : (), # FIXME: NEEDS CUSTOM SORTING
				'grid_view'    : ('street', 'number', 'num_slash', 'num_suffix', 'building', 'entrnum', 'postindex'),
				'form_view'    : ('street', 'number', 'num_slash', 'num_suffix', 'building', 'house_groups', 'entrnum', 'postindex'),
				'easy_search'  : ('number',),
				'detail_pane'  : ('netprofile_core.views', 'dpane_simple'),
				'extra_search' : (
					CheckboxGroupFilter('hg', _filter_hgroup,
						title=_('House Group'),
						data='NetProfile.store.geo.HouseGroup',
						value_field='ahgid',
						display_field='name'
					),
					AddressFilter('address', _filter_address,
						title=_('Address')
					)
				),

				'create_wizard' : Wizard(
					Step('street', 'number', 'num_slash', 'num_suffix', 'building', title=_('Basic house data')),
					Step('house_groups', 'entrnum', 'postindex', title=_('Additional house data')),
					title=_('Add new house')
				)
			}
		}
	)

	id = Column(
		'houseid',
		UInt32(),
		Sequence('houseid_seq'),
		Comment('House ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	street_id = Column(
		'streetid',
		UInt32(),
		ForeignKey('addr_streets.streetid', name='addr_houses_fk_streetid', ondelete='CASCADE', onupdate='CASCADE'),
		Comment('Street ID'),
		nullable=False,
		info={
			'header_string' : _('Street'),
			'filter_type'   : 'list'
		}
	)
	number = Column(
		UInt16(),
		Comment('House number'),
		nullable=False,
		default=0,
		server_default=text('0'),
		info={
			'header_string' : _('Number')
		}
	)
	building = Column(
		UInt16(),
		Comment('House building'),
		nullable=False,
		default=0,
		server_default=text('0'),
		info={
			'header_string' : _('Building')
		}
	)
	second_number = Column(
		'num_slash',
		UInt16(),
		Comment('Second house number'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Second Num.')
		}
	)
	number_suffix = Column(
		'num_suffix',
		Unicode(32),
		Comment('House number suffix'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Num. Suffix')
		}
	)
	entrances = Column(
		'entrnum',
		UInt8(),
		Comment('Number of entrances'),
		nullable=False,
		default=1,
		server_default=text('1'),
		info={
			'header_string' : _('Entr. #')
		}
	)
	postal_code = Column(
		'postindex',
		Unicode(8),
		Comment('Postal code'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Postal Code')
		}
	)

	places = relationship(
		'Place',
		backref=backref('house', innerjoin=True),
		cascade='all, delete-orphan',
		passive_deletes=True
	)
	house_groupmap = relationship(
		'HouseGroupMapping',
		backref=backref('house', innerjoin=True),
		cascade='all, delete-orphan',
		passive_deletes=True
	)

	house_groups = association_proxy(
		'house_groupmap',
		'group',
		creator=lambda v: HouseGroupMapping(group=v)
	)

	@classmethod
	def __augment_query__(cls, sess, query, params):
		query = query.join(House.street).options(contains_eager(House.street))
		flt = {}
		if '__filter' in params:
			flt.update(params['__filter'])
		if '__ffilter' in params:
			flt.update(params['__ffilter'])
		if ('districtid' in flt) and ('eq' in flt['districtid']):
			val = int(flt['districtid']['eq'])
			if val > 0:
				query = query.filter(Street.district_id == val)
		elif ('cityid' in flt) and ('eq' in flt['cityid']):
			val = int(flt['cityid']['eq'])
			sq = sess.query(District).filter(District.city_id == val)
			val = [d.id for d in sq]
			if len(val) > 0:
				query = query.filter(Street.district_id.in_(val))
			else:
				query = query.filter(False)
		return query

	@classmethod
	def __augment_result__(cls, sess, res, params):
		populate_related_list(
			res, 'id', 'house_groupmap', HouseGroupMapping,
			sess.query(HouseGroupMapping),
			None, 'house_id'
		)
		return res

	def __str__(self):
		req = get_current_request()
		loc = get_localizer(req)

		l = [str(self.street), str(self.number)]
		if self.number_suffix:
			l.append(self.number_suffix)
		if self.second_number:
			l.append('/' + str(self.second_number))
		if self.building:
			l.append(loc.translate(_('bld.')))
			l.append(str(self.building))
		return ' '.join(l)

class Place(Base):
	"""
	Place object. Used for any container, shelf or storage space.
	"""
	__tablename__ = 'addr_places'
	__table_args__ = (
		Comment('Places'),
		Index('addr_places_u_number', 'number', unique=True),
		Index('addr_places_i_houseid', 'houseid'),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'cap_menu'     : 'BASE_GEO',
				'cap_read'     : 'GEO_LIST',
				'cap_create'   : 'GEO_CREATE',
				'cap_edit'     : 'GEO_EDIT',
				'cap_delete'   : 'GEO_DELETE',

				'show_in_menu' : 'admin',
				'menu_name'    : _('Places'),
				'menu_order'   : 80,
				'default_sort' : (), # FIXME: SEE HOUSES
				'grid_view'    : ('house', 'number', 'name', 'entrance', 'floor', 'descr'),
				'easy_search'  : ('number',),
				'detail_pane'  : ('netprofile_core.views', 'dpane_simple'),

				'create_wizard' : SimpleWizard(title=_('Add new place'))
			}
		}
	)

	id = Column(
		'placeid',
		UInt32(),
		Sequence('placeid_seq'),
		Comment('Place ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	house_id = Column(
		'houseid',
		UInt32(),
		ForeignKey('addr_houses.houseid', name='addr_places_fk_houseid', ondelete='CASCADE', onupdate='CASCADE'),
		Comment('House ID'),
		nullable=False,
		info={
			'header_string' : _('House'),
			'filter_type'   : 'none'
		}
	)
	number = Column(
		UInt16(),
		Comment('Place number'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Number')
		}
	)
	name = Column(
		Unicode(255),
		Comment('Place name'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Name')
		}
	)
	entrance = Column(
		UInt8(),
		Comment('Entrance number'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Entr. #')
		}
	)
	floor = Column(
		UInt8(),
		Comment('Floor number'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Floor #')
		}
	)
	description = Column(
		'descr',
		UnicodeText(),
		Comment('Place description'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Description')
		}
	)

	def __str__(self):
		return '%s' % str(self.number)

class HouseGroup(Base):
	"""
	Used for grouping arbitrary houses. Each house can be part of any
	number of groups.
	"""
	__tablename__ = 'addr_hgroups_def'
	__table_args__ = (
		Comment('House groups'),
		Index('addr_hgroups_def_u_name', 'name', unique=True),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'cap_menu'     : 'BASE_GEO',
				'cap_read'     : 'GEO_LIST',
				'cap_create'   : 'GEO_CREATE',
				'cap_edit'     : 'GEO_EDIT',
				'cap_delete'   : 'GEO_DELETE',

				'show_in_menu' : 'admin',
				'menu_name'    : _('House Groups'),
				'menu_order'   : 90,
				'default_sort' : ({ 'property': 'name' ,'direction': 'ASC' },),
				'grid_view'    : ('name', 'descr'),
				'easy_search'  : ('name',),
				'detail_pane'  : ('netprofile_core.views', 'dpane_simple'),

				'create_wizard' : SimpleWizard(title=_('Add new house group'))
			}
		}
	)

	id = Column(
		'ahgid',
		UInt32(),
		Sequence('ahgid_seq'),
		Comment('House group ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	name = Column(
		Unicode(255),
		Comment('Place name'),
		nullable=False,
		info={
			'header_string' : _('Name')
		}
	)
	description = Column(
		'descr',
		UnicodeText(),
		Comment('Place description'),
		nullable=True,
		default=None,
		server_default=text('NULL'),
		info={
			'header_string' : _('Description')
		}
	)
	mappings = relationship(
		'HouseGroupMapping',
		backref=backref('group', innerjoin=True, lazy='joined'),
		cascade='all, delete-orphan',
		passive_deletes=True
	)

	houses = association_proxy(
		'mappings',
		'house'
	)

	def __str__(self):
		return '%s' % str(self.name)

class HouseGroupMapping(Base):
	"""
	Mapping between houses and house groups.
	"""
	__tablename__ = 'addr_hgroups_houses'
	__table_args__ = (
		Comment('House group memberships'),
		Index('addr_hgroups_houses_u_member', 'ahgid', 'houseid', unique=True),
		Index('addr_hgroups_houses_i_houseid', 'houseid'),
		{
			'mysql_engine'  : 'InnoDB',
			'mysql_charset' : 'utf8',
			'info'          : {
				'menu_name'    : _('House Groups'),

				'cap_menu'     : 'BASE_GEO',
				'cap_read'     : 'GEO_LIST',
				'cap_create'   : 'GEO_CREATE',
				'cap_edit'     : 'GEO_EDIT',
				'cap_delete'   : 'GEO_DELETE',

				'default_sort' : (),
				'grid_view'    : ('group', 'house'),
				'detail_pane'  : ('netprofile_core.views', 'dpane_simple')
			}
		}
	)

	id = Column(
		'ahghid',
		UInt32(),
		Sequence('ahghid_seq'),
		Comment('House group membership ID'),
		primary_key=True,
		nullable=False,
		info={
			'header_string' : _('ID')
		}
	)
	group_id = Column(
		'ahgid',
		UInt32(),
		ForeignKey('addr_hgroups_def.ahgid', name='addr_hgroups_houses_fk_ahgid', ondelete='CASCADE', onupdate='CASCADE'),
		Comment('House group ID'),
		nullable=False,
		info={
			'header_string' : _('Group')
		}
	)
	house_id = Column(
		'houseid',
		UInt32(),
		ForeignKey('addr_houses.houseid', name='addr_hgroups_houses_fk_houseid', ondelete='CASCADE', onupdate='CASCADE'),
		Comment('House ID'),
		nullable=False,
		info={
			'header_string' : _('House')
		}
	)

