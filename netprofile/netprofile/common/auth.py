#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import (
	unicode_literals,
	print_function,
	absolute_import,
	division
)

import hashlib
import random
import string
import time

from zope.interface import implementer
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.security import (
	Authenticated,
	Everyone
)

class PluginPolicySelected(object):
	def __init__(self, request, policy):
		self.request = request
		self.policy = policy

@implementer(IAuthenticationPolicy)
class PluginAuthenticationPolicy(object):
	def __init__(self, default, routes=None):
		self._default = default
		if routes is None:
			routes = {}
		self._routes = routes

	def add_plugin(self, route, policy):
		self._routes[route] = policy

	def match(self, request):
		if hasattr(request, 'auth_policy'):
			return request.auth_policy
		cur = None
		cur_len = 0
		for route, plug in self._routes.items():
			r_len = len(route)
			if r_len <= cur_len:
				continue
			if route == request.path[:r_len]:
				cur = plug
				cur_len = r_len
		if cur:
			request.auth_policy = cur
		else:
			request.auth_policy = self._default
		return request.auth_policy

	def authenticated_userid(self, request):
		return self.match(request).authenticated_userid(request)

	def unauthenticated_userid(self, request):
		return self.match(request).unauthenticated_userid(request)

	def effective_principals(self, request):
		return self.match(request).effective_principals(request)

	def remember(self, request, principal, **kw):
		return self.match(request).remember(request, principal, **kw)

	def forget(self, request):
		return self.match(request).forget(request)

_TOKEN_FILTER_MAP = (
	[chr(n) for n in range(32)] +
	[chr(127), '\\', '"']
)
_TOKEN_FILTER_MAP = dict.fromkeys(_TOKEN_FILTER_MAP, None)

def _filter_token(tok):
	return str(tok).translate(_TOKEN_FILTER_MAP)

def _format_kvpairs(**kwargs):
	return ', '.join('{0!s}="{1}"'.format(k, _filter_token(v)) for (k, v) in kwargs.items())

def _generate_nonce(ts, secret, salt=None, chars=string.hexdigits.upper()):
	# TODO: Add IP-address to nonce
	if not salt:
		try:
			rng = random.SystemRandom()
		except NotImplementedError:
			rng = random
		salt = ''.join(rng.choice(chars) for i in range(16))
	ctx = hashlib.md5(('%s:%s:%s' % (ts, salt, secret)).encode())
	return ('%s:%s:%s' % (ts, salt, ctx.hexdigest()))

def _is_valid_nonce(nonce, secret):
	comp = nonce.split(':')
	if len(comp) != 3:
		return False
	calc_nonce = _generate_nonce(comp[0], secret, comp[1])
	if nonce == calc_nonce:
		return True
	return False

def _generate_digest_challenge(ts, secret, realm, opaque, stale=False):
	nonce = _generate_nonce(ts, secret)
	return 'Digest %s' % (_format_kvpairs(
		realm=realm,
		qop='auth',
		nonce=nonce,
		opaque=opaque,
		algorithm='MD5',
		stale='true' if stale else 'false'
	),)

def _add_www_authenticate(request, secret, realm):
	resp = request.response
	if not resp.www_authenticate:
		resp.www_authenticate = _generate_digest_challenge(
			round(time.time()),
			secret, realm, 'NPDIGEST'
		)

def _parse_authorization(request, secret, realm):
	authz = request.authorization
	if (not authz) or (len(authz) != 2) or (authz[0] != 'Digest'):
		_add_www_authenticate(request, secret, realm)
		return None
	params = authz[1]
	if 'algorithm' not in params:
		params['algorithm'] = 'MD5'
	for required in ('username', 'realm', 'nonce', 'uri', 'response', 'cnonce', 'nc', 'opaque'):
		if (required not in params) or ((required == 'opaque') and (params['opaque'] != 'NPDIGEST')):
			_add_www_authenticate(request, secret, realm)
			return None
	return params

@implementer(IAuthenticationPolicy)
class DigestAuthenticationPolicy(object):
	def __init__(self, secret, callback, realm='Realm'):
		self.secret = secret
		self.callback = callback
		self.realm = realm

	def authenticated_userid(self, request):
		params = _parse_authorization(request, self.secret, self.realm)
		if params is None:
			return None
		if not _is_valid_nonce(params['nonce'], self.secret):
			_add_www_authenticate(request, self.secret, self.realm)
			return None
		userid = params['username']
		if self.callback(params, request) is not None:
			return userid
		_add_www_authenticate(request, self.secret, self.realm)

	def unauthenticated_userid(self, request):
		params = _parse_authorization(request, self.secret, self.realm)
		if params is None:
			return None
		if not _is_valid_nonce(params['nonce'], self.secret):
			_add_www_authenticate(request, self.secret, self.realm)
			return None
		return params['username']

	def effective_principals(self, request):
		pass

	def remember(self, request, principal, *kw):
		return []

	def forget(self, request):
		pass

