#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-
#
# NetProfile: LDAP module
# © Copyright 2013-2015 Alex 'Unik' Unigovsky
#
# This file is part of NetProfile.
# NetProfile is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later
# version.
#
# NetProfile is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General
# Public License along with NetProfile. If not, see
# <http://www.gnu.org/licenses/>.

from __future__ import (
	unicode_literals,
	print_function,
	absolute_import,
	division
)

import ldap3
import ssl
from sqlalchemy import event
from pyramid.settings import (
	asbool,
	aslist
)
from netprofile.common.hooks import register_hook
from netprofile.common.util import make_config_dict

LDAPConn = None

_LDAP_ORM_CFG = 'netprofile.ldap.orm.%s.%s'
_ldap_active = False

# model-level:
# ldap_classes
# ldap_rdn

# column-level:
# ldap_attr (can be a list)
# ldap_value (can be a callable)

#class LDAPConnector(object):
#	def __init__(self, pool, req):
#		self.pool = pool
#		self.req = req
#
#	def connection(self, login=None, pwd=None):
#		return self.pool.connection(login, pwd)

def _gen_search_attrs(em, settings):
	attrs = []
	sname = _LDAP_ORM_CFG % (em.name, 'base')
	if sname not in settings:
		sname = _LDAP_ORM_CFG % ('default', 'base')
	attrs.append(settings.get(sname))

	sname = _LDAP_ORM_CFG % (em.name, 'scope')
	if sname not in settings:
		sname = _LDAP_ORM_CFG % ('default', 'scope')
	val = settings.get(sname, 'base')
	if val == 'base':
		val = ldap3.BASE
	elif val == 'one':
		val = ldap3.LEVEL
	elif val == 'sub':
		val = ldap3.SUBTREE
	attrs.append(val)

	return attrs

def _gen_attrlist(cols, settings, info):
	object_classes = info.get('ldap_classes')
	def _attrlist(tgt):
		attrs = {
			'objectClass' : object_classes
		}
		for cname, col in cols.items():
			try:
				ldap_attr = col.column.info['ldap_attr']
			except KeyError:
				continue
			prop = tgt.__mapper__.get_property_by_column(col.column)
			if 'ldap_value' in col.column.info:
				cb = col.column.info['ldap_value']
				try:
					cb = getattr(tgt, cb)
				except AttributeError:
					continue
				if not callable(cb):
					continue
				try:
					val = cb(settings)
				except ValueError:
					continue
			else:
				# TODO: handle multiple values
				val = getattr(tgt, prop.key)
			# FIXME: rewrite bytes/str handling for ldap3
			if (not isinstance(val, bytes)) and (val is not None):
				if not isinstance(val, str):
					val = str(val)
				val = val.encode()
			if isinstance(ldap_attr, (list, tuple)):
				for la in ldap_attr:
					attrs[la] = [val]
			else:
				if val is None:
					attrs[ldap_attr] = None
				else:
					attrs[ldap_attr] = [val]
		extra = getattr(tgt, 'ldap_attrs', None)
		if extra and callable(extra):
			attrs.update(extra(settings))
		return attrs
	return _attrlist

def get_rdn(obj):
	ldap_rdn = obj.__table__.info.get('ldap_rdn')
	col = obj.__table__.columns[ldap_rdn]
	prop = obj.__mapper__.get_property_by_column(col)
	try:
		ldap_attr = col.info['ldap_attr']
	except KeyError:
		ldap_attr = ldap_rdn
	if isinstance(ldap_attr, (list, tuple)):
		ldap_attr = ldap_attr[0]
	return '%s=%s' % (ldap_attr, getattr(obj, prop.key))

def get_dn(obj, settings):
	sname = _LDAP_ORM_CFG % (obj.__class__.__name__, 'base')
	if sname not in settings:
		sname = _LDAP_ORM_CFG % ('default', 'base')
	base = settings.get(sname)
	return '%s,%s' % (get_rdn(obj), base)

def _gen_ldap_object_rdn(em, rdn_col):
	col = em.get_column(rdn_col)
	prop = em.model.__mapper__.get_property_by_column(col.column)
	try:
		ldap_attr = col.column.info['ldap_attr']
	except KeyError:
		ldap_attr = rdn_col
	if isinstance(ldap_attr, (list, tuple)):
		ldap_attr = ldap_attr[0]
	def _ldap_object_rdn(tgt):
		return '%s=%s' % (ldap_attr, getattr(tgt, prop.key))
	return _ldap_object_rdn

def _gen_ldap_object_load(em, info, settings):
	attrs = _gen_search_attrs(em, settings)
	rdn_attr = info.get('ldap_rdn')
	object_classes = info.get('ldap_classes')
	object_classes = '(objectClass=' + ')(objectClass='.join(object_classes) + ')'
	get_rdn = _gen_ldap_object_rdn(em, rdn_attr)
	def _ldap_object_load(tgt, ctx):
		ret = None
		rdn = get_rdn(tgt)
		flt = '(&(%s)%s)' % (rdn, object_classes)
		with LDAPConn as lc:
			ret = lc.search_s(attrs[0], attrs[1], flt)
		if isinstance(ret, list) and (len(ret) > 0):
			tgt._ldap_data = ret[0]
	return _ldap_object_load

def _gen_ldap_object_store(em, info, settings):
	cols = em.get_read_columns()
	cfg = _gen_search_attrs(em, settings)
	rdn_attr = info.get('ldap_rdn')
	get_attrlist = _gen_attrlist(cols, settings, info)
	get_rdn = _gen_ldap_object_rdn(em, rdn_attr)
	def _ldap_object_store(mapper, conn, tgt):
		attrs = get_attrlist(tgt)
		dn = '%s,%s' % (get_rdn(tgt), cfg[0])
		ldap_data = getattr(tgt, '_ldap_data', False)
		with LDAPConn as lc:
			if ldap_data:
				if dn != ldap_data[0]:
					lc.rename_s(ldap_data[0], dn)
					tgt._ldap_data = ldap_data = (dn, ldap_data[1])
				xattrs = []
				del_attrs = []
				for attr in attrs:
					val = attrs[attr]
					if val is None:
						if attr in ldap_data[1]:
							xattrs.append((ldap.MOD_DELETE, attr, val))
						del_attrs.append(attr)
					else:
						xattrs.append((ldap.MOD_REPLACE, attr, val))
				for attr in del_attrs:
					del attrs[attr]
				lc.modify_s(ldap_data[0], xattrs)
				tgt._ldap_data[1].update(attrs)
			else:
				lc.add_s(dn, list(attrs.items()))
				tgt._ldap_data = (dn, attrs)
	return _ldap_object_store

def _gen_ldap_object_delete(em, info, settings):
	cfg = _gen_search_attrs(em, settings)
	rdn_attr = info.get('ldap_rdn')
	get_rdn = _gen_ldap_object_rdn(em, rdn_attr)
	def _ldap_object_delete(mapper, conn, tgt):
		dn = '%s,%s' % (get_rdn(tgt), cfg[0])
		with LDAPConn as lc:
			lc.delete_s(dn)
	return _ldap_object_delete

@register_hook('np.model.load')
def _proc_model_ldap(mmgr, model):
	if not _ldap_active:
		return
	info = model.model.__table__.info
	if ('ldap_classes' not in info) or ('ldap_rdn' not in info):
		return

	settings = mmgr.cfg.registry.settings

	event.listen(model.model, 'load', _gen_ldap_object_load(model, info, settings))
	event.listen(model.model, 'after_insert', _gen_ldap_object_store(model, info, settings))
	event.listen(model.model, 'after_update', _gen_ldap_object_store(model, info, settings))
	event.listen(model.model, 'after_delete', _gen_ldap_object_delete(model, info, settings))

def includeme(config):
	global _ldap_active, LDAPConn

	settings = config.registry.settings
	conn_cfg = make_config_dict(settings, 'netprofile.ldap.connection.')
	ssl_cfg = make_config_dict(conn_cfg, 'ssl.')
	auth_cfg = make_config_dict(conn_cfg, 'auth.')

	ldap_host = None
	server_opts = {}
	tls_opts = {}
	conn_opts = { 'lazy' : True }

	if 'uri' in conn_cfg:
		ldap_host = conn_cfg['uri']
	elif 'host' in conn_cfg:
		ldap_host = conn_cfg['host']

	if 'port' in conn_cfg:
		server_opts['port'] = conn_cfg['port']
	if 'protocol' in conn_cfg:
		conn_opts['version'] = conn_cfg['protocol']
	if 'type' in auth_cfg:
		value = auth_cfg['type']
		proc = None
		if value in ('anon', 'anonymous'):
			proc = ldap3.AUTH_ANONYMOUS
		elif value == 'simple':
			proc = ldap3.AUTH_SIMPLE
		elif value == 'sasl':
			proc = ldap3.AUTH_SASL
		elif value == 'ntlm':
			proc = ldap3.NTLM
		if proc:
			conn_opts['authentication'] = proc
	if ('user' in auth_cfg) and ('password' in auth_cfg):
		conn_opts['user'] = auth_cfg['user']
		conn_opts['password'] = auth_cfg['password']
		if 'authentication' not in conn_opts:
			conn_opts['authentication'] = ldap3.AUTH_SIMPLE
		bind = None
		bind_cfg = auth_cfg.get('bind')
		if bind_cfg == 'none':
			bind = ldap3.AUTO_BIND_NONE
		elif bind_cfg == 'no-tls':
			bind = ldap3.AUTO_BIND_NO_TLS
		elif bind_cfg == 'tls-before-bind':
			bind = ldap3.AUTO_BIND_TLS_BEFORE_BIND
		elif bind_cfg == 'tls-after-bind':
			bind = ldap3.AUTO_BIND_TLS_AFTER_BIND
		if bind:
			conn_opts['auto_bind'] = bind

	if ('key.file' in ssl_cfg) and ('cert.file' in ssl_cfg):
		tls_opts['local_private_key_file'] = ssl_cfg['key.file']
		tls_opts['local_certificate_file'] = ssl_cfg['cert.file']
	# TODO: version= in tls_opts
	if 'validate' in ssl_cfg:
		value = ssl_cfg['validate']
		if value == 'none':
			tls_opts['validate'] = ssl.CERT_NONE
		elif value == 'optional':
			tls_opts['validate'] = ssl.CERT_OPTIONAL
		elif value == 'required':
			tls_opts['validate'] = ssl.CERT_REQUIRED
	if 'ca.file' in ssl_cfg:
		tls_opts['ca_certs_file'] = ssl_cfg['ca.file']
	if 'altnames' in ssl_cfg:
		tls_opts['valid_names'] = aslist(ssl_cfg['altnames'])
	if 'ca.path' in ssl_cfg:
		tls_opts['ca_certs_path'] = ssl_cfg['ca.path']
	if 'ca.data' in ssl_cfg:
		tls_opts['ca_certs_data'] = ssl_cfg['ca.data']
	if 'key.password' in ssl_cfg:
		tls_opts['local_private_key_password'] = ssl_cfg['key.password']

	tls = None
	if len(tls_opts):
		tls = ldap3.Tls(**tls_opts)
		server_opts['use_ssl'] = True

	server = ldap3.Server(ldap_host, tls=tls, **server_opts)
	LDAPConn = ldap3.Connection(server, client_strategy=ldap3.REUSABLE, **conn_opts)

	def get_system_ldap(request):
		return LDAPConn
	config.add_request_method(get_system_ldap, str('ldap'), reify=True)

	_ldap_active = True

	config.scan()

