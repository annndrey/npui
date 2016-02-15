#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-
#
# NetProfile: Devices module - Bundled device handlers
# © Copyright 2015-2016 Alex 'Unik' Unigovsky
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

import snimpy.manager as mgr
from snimpy.snmp import SNMPNoSuchObject

from pyramid.decorator import reify

from netprofile.common import ipaddr

class TableProxy(object):
	def __init__(self, hdl, table, idx):
		self._hdl = hdl
		self._table = table
		self._idx = idx

	def __getattr__(self, attr):
		return getattr(self._hdl.snmp_ro, attr)[self._idx]

class NetworkDeviceHandler(object):
	def __init__(self, devtype, dev):
		self.type = devtype
		self.dev = dev

	@reify
	def snmp_ro(self):
		return self.dev.snmp_context()

	@reify
	def snmp_rw(self):
		if not self.dev.snmp_has_rw_context:
			return self.snmp_ro
		return self.dev.snmp_context(is_rw=True)

	@property
	def interfaces(self):
		mgr.load('IF-MIB')
		tbl = self.snmp_ro.ifIndex.proxy.table
		for idx in self.snmp_ro.ifIndex:
			yield TableProxy(self, tbl, idx)

	@property
	def base_ports(self):
		mgr.load('BRIDGE-MIB')
		tbl = self.snmp_ro.dot1dBasePort.proxy.table
		for baseport in self.snmp_ro.dot1dBasePort:
			yield TableProxy(self, tbl, baseport)

	@property
	def vlans(self):
		if self.type.has_flag('SNMP: CISCO-VTP-MIB'):
			mgr.load('CISCO-VTP-MIB')
			tbl = self.snmp_ro.vtpVlanState.proxy.table
			for mgmtid, vlanid in self.snmp_ro.vtpVlanState:
				yield TableProxy(self, tbl, (mgmtid, vlanid))
		else:
			mgr.load('Q-BRIDGE-MIB')
			tbl = self.snmp_ro.dot1qVlanFdbId.proxy.table
			for timemark, vlanid in self.snmp_ro.dot1qVlanFdbId:
				yield TableProxy(self, tbl, (timemark, vlanid))

	def ifindex_by_address(self, addr):
		if not self.type.has_flag('SNMP: IP-MIB'):
			return None
		mgr.load('IP-MIB')

		if isinstance(addr, ipaddr.IPv4Address):
			addrtype = 1
		elif isinstance(addr, ipaddr.IPv6Address):
			addrtype = 2
		else:
			return None

		try:
			return int(self.snmp_ro.ipAddressIfIndex[addrtype, str(addr)])
		except SNMPNoSuchObject:
			pass
		if addrtype == 1:
			try:
				return int(self.snmp_ro.ipAdEntIfIndex[str(addr)])
			except SNMPNoSuchObject:
				pass
		return None

	def arp_table(self, ifindex=None):
		tfilter = []
		if ifindex is not None:
			tfilter.append(ifindex)
		tbl = []
		if self.type.has_flag('SNMP: IP-MIB'):
			mgr.load('IP-MIB')
			try:
				for idx, phys in self.snmp_ro.ipNetToMediaPhysAddress.iteritems(*tfilter):
					tbl.append((int(idx[0]), ipaddr.IPv4Address(idx[1]), phys._toBytes()))
			except SNMPNoSuchObject:
				for idx, phys in self.snmp_ro.ipNetToPhysicalPhysAddress.iteritems(*tfilter):
					tbl.append((int(idx[0]), ipaddr.IPv4Address(idx[1]), phys._toBytes()))
		return tbl

