/**
 * @class NetProfile.panel.FileBrowser
 * @extends Ext.panel.Panel
 */
Ext.define('NetProfile.panel.FileBrowser', {
	extend: 'Ext.panel.Panel',
	alias: 'widget.filebrowser',
	stateId: 'npws_filebrowser',
	stateful: true,
	requires: [
		'Ext.menu.*',
		'Ext.grid.*',
		'Ext.XTemplate',
		'NetProfile.form.FileUpload',
		'NetProfile.store.core.File',
		'NetProfile.view.FileIconView',
		'Ext.ux.form.RightsBitmaskField'
	],

	border: 0,
	layout: 'fit',

	store: null,
	view: null,
	views: {},
	folder: null,
	viewType: 'icon',
	sortType: 'fname',
	sortDir: 'ASC',
	searchStr: null,
	uploadUrl: NetProfile.baseURL + '/core/file/ul',

	emptyText: 'Folder is empty',

	viewText: 'View',
	viewAsIconsText: 'Icons',
	viewAsListText: 'List',
	viewAsGridText: 'Grid',

	sortText: 'Sort',
	sortByNameText: 'By Filename',
	sortByCTimeText: 'By Creation Time',
	sortByMTimeText: 'By Modification Time',
	sortBySizeText: 'By Size',

	sortAscText: 'Sort Ascending',
	sortDescText: 'Sort Descending',

	btnDeleteText: 'Delete',

	deleteTipText: 'Delete File',
	deleteMsgText: 'Are you sure you want to delete selected file?',
	deleteManyTipText: 'Delete Files',
	deleteManyMsgText: 'Are you sure you want to delete selected files?',

	btnUploadText: 'Upload',

	btnRenameText: 'Rename',
	btnPropsText: 'Properties',
	btnDownloadText: 'Download',

	searchEmptyText: 'Search...',

	gridNameText: 'Name',
	gridSizeText: 'Size',
	gridCreatedText: 'Created',
	gridModifiedText: 'Last Modified',

	dragText: 'Move or attach files ({0})',

	bytesText: 'B',
	kibText: 'KiB',
	mibText: 'MiB',
	gibText: 'GiB',
	tibText: 'TiB',
	pibText: 'PiB',
	eibText: 'EiB',

	initComponent: function()
	{
		this.view = null;
		this.views = {};
		this.folder = null;
		this.kmap = null;

		this.selectEditable = Ext.dom.Query.compile('.x-editable');

		if(!this.store)
			this.store = Ext.create('NetProfile.store.core.File', {
				autoDestroy: true,
				autoLoad: false,
				autoSync: false,
				buffered: false,
				pageSize: -1,
				storeId: null,
				proxy: {
					type: 'core_File'
				},
				listeners: {
					load: function(recs, op, success)
					{
						this.fireEvent('load', this, recs, op, success);
					},
					scope: this
				}
			});
		this.ctxMenu = Ext.create('Ext.menu.Menu', {
			items: [{
				itemId: 'ren_item',
				text: this.btnRenameText,
				iconCls: 'ico-doc-ren',
				handler: function(btn, ev)
				{
					var rec, plug, view;

					rec = this.ctxMenu.record;
					if(!rec || Ext.isArray(rec))
						return false;
					switch(this.viewType)
					{
						case 'icon':
						case 'list':
							plug = this.view.getPlugin('editor');
							view = this.view.getNode(rec);
							if(!view)
								return false;
							view = this.selectEditable(view);
							if(plug && view && view.length)
							{
								plug.startEdit(view[0], rec.get(plug.dataIndex));
								plug.activeRecord = rec;
							}
							break;
						case 'grid':
							plug = this.view.getPlugin('editor');
							view = this.view.getView();
							if(plug && view)
								plug.startEdit(rec, view.getHeaderAtIndex(1));
							break;
						default:
							break;
					}
				},
				scope: this
			}, {
				text: this.btnPropsText,
				iconCls: 'ico-props',
				handler: function(btn, ev)
				{
					var pb = Ext.getCmp('npws_propbar'),
						rec = this.ctxMenu.record,
						dp = NetProfile.view.grid.core.File.prototype.detailPane,
						can_wr = true;

					if(this.folder && !this.folder.get('allow_write'))
						can_wr = false;
					if(!pb || !rec || !dp)
						return false;
					if(Ext.isArray(rec))
					{
						var r;
						for(r in rec)
						{
							rec[r].readOnly = !can_wr || !rec[r].get('allow_write');
							pb.addRecordTab('core', 'File', dp, rec[r]);
						}
					}
					else
					{
						rec.readOnly = !can_wr || !rec.get('allow_write');
						pb.addRecordTab('core', 'File', dp, rec);
					}
					pb.show();
				},
				scope: this
			}, {
				itemId: 'dl_item',
				text: this.btnDownloadText,
				iconCls: 'ico-save',
				handler: function(btn, ev)
				{
					var rec;

					rec = this.ctxMenu.record;
					if(!rec)
						return false;
					return this.onFileOpen(rec);
				},
				scope: this
			}, '-', {
				itemId: 'del_item',
				text: this.btnDeleteText,
				iconCls: 'ico-delete',
				handler: function(btn, ev)
				{
					var rec;

					rec = this.ctxMenu.record;
					if(!rec)
						return false;
					if(!Ext.isArray(rec))
						rec = [rec];
					return this.deleteRecords(rec);
				},
				scope: this
			}]
		});
		this.selectedRecords = [];
		this.dockedItems = [{
			xtype: 'fileuploadform',
			dock: 'left',
			hidden: true,
			url: this.uploadUrl,
			itemId: 'fileupload'
		}];
		this.tbar = [{
			text: this.viewText,
			iconCls: 'ico-view',
			menu: [{
				itemId: 'icon',
				text: this.viewAsIconsText,
				checked: true,
				group: 'view',
				checkHandler: this.onViewChange,
				scope: this
			}, {
				itemId: 'list',
				text: this.viewAsListText,
				checked: false,
				group: 'view',
				checkHandler: this.onViewChange,
				scope: this
			}, {
				itemId: 'grid',
				text: this.viewAsGridText,
				checked: false,
				group: 'view',
				checkHandler: this.onViewChange,
				scope: this
			}]
		}, {
			text: this.sortText,
			iconCls: 'ico-sort',
			menu: [{
				itemId: 'fname',
				text: this.sortByNameText,
				checked: true,
				group: 'sort',
				checkHandler: this.onSortChange,
				scope: this
			}, {
				itemId: 'ctime',
				text: this.sortByCTimeText,
				checked: false,
				group: 'sort',
				checkHandler: this.onSortChange,
				scope: this
			}, {
				itemId: 'mtime',
				text: this.sortByMTimeText,
				checked: false,
				group: 'sort',
				checkHandler: this.onSortChange,
				scope: this
			}, {
				itemId: 'size',
				text: this.sortBySizeText,
				checked: false,
				group: 'sort',
				checkHandler: this.onSortChange,
				scope: this
			}, '-', {
				itemId: 'ASC',
				text: this.sortAscText,
				checked: true,
				group: 'sdir',
				checkHandler: this.onSortDirChange,
				scope: this
			}, {
				itemId: 'DESC',
				text: this.sortDescText,
				checked: true,
				group: 'sdir',
				checkHandler: this.onSortDirChange,
				scope: this
			}]
		}, '-', {
			text: this.btnDeleteText,
			iconCls: 'ico-delete',
			itemId: 'btn_delete',
			disabled: true,
			handler: function(btn, ev)
			{
				var me = this;

				this.deleteRecords(this.selectedRecords, function()
				{
					me.selectedRecords = [];
				});
			},
			scope: this
		}, '-', {
			text: this.btnUploadText,
			iconCls: 'ico-upload',
			itemId: 'btn_upload',
			disabled: true,
			enableToggle: true,
			toggleHandler: function(btn, state)
			{
				var me = this,
					fup = me.getDockedComponent('fileupload');

				fup.setVisible(state);
			},
			scope: this
		}, '->', {
			xtype: 'textfield',
			cls: 'np-ssearch-field',
			itemId: 'search_fld',
			hideLabel: true,
			emptyText: this.searchEmptyText,
			listeners: {
				change: function(fld, newval, oldval)
				{
					this.fireEvent('searchchange', newval);
				},
				scope: this
			}
		}];
		this.callParent(arguments);

		this.on({
			beforedestroy: this.onBeforeDestroy,
			beforerender: this.onBeforeRender,
			afterrender: this.onAfterRender,
			folderupdate: this.onFolderUpdate,
			searchchange: {
				fn: this.onSearchChange,
				buffer: 500
			},
			filesdropped: function(view, files, ev)
			{
				this.uploadFileList(files);
			}
		});
	},
    getState: function()
	{
		var state = this.callParent();

		state = this.addPropertyToState(state, 'viewType');
		state = this.addPropertyToState(state, 'sortType');
		state = this.addPropertyToState(state, 'sortDir');
		return state;
	},
	onBeforeDestroy: function(me)
	{
		Ext.Object.each(me.views, function(k, v)
		{
			if(v !== me.view)
				Ext.destroy(v);
		});
		if(me.ctxMenu)
		{
			me.ctxMenu.hide();
			Ext.destroy(me.ctxMenu);
			me.ctxMenu = null;
		}
		return true;
	},
	onBeforeRender: function(me)
	{
		this.updateCheckItems(true);
		this.renderView();
		this.fireEvent('folderupdate', this);
		return true;
	},
	onAfterRender: function(me)
	{
		var el = me.getEl();

		el.on({
			drop: this.onDrop,
			scope: this
		});
		el.dom.ondragenter = Ext.Function.bind(this.onDragTest, this);
		el.dom.ondragover = Ext.Function.bind(this.onDragTest, this);
	},
	updateCheckItems: function(sup)
	{
		var me = this;

		Ext.Array.forEach(me.query('menucheckitem[group=view]'), function(cki)
		{
			if(cki.itemId == me.viewType)
				cki.setChecked(true, sup);
			else
				cki.setChecked(false, sup);
		});
		Ext.Array.forEach(me.query('menucheckitem[group=sort]'), function(cki)
		{
			if(cki.itemId == me.sortType)
				cki.setChecked(true, sup);
			else
				cki.setChecked(false, sup);
		});
		Ext.Array.forEach(me.query('menucheckitem[group=sdir]'), function(cki)
		{
			if(cki.itemId == me.sortDir)
				cki.setChecked(true, sup);
			else
				cki.setChecked(false, sup);
		});
	},
	setFolder: function(frec)
	{
		this.fireEvent('beforefolderupdate', this, frec);
		this.folder = frec;
		this.updateStore();
		this.fireEvent('folderupdate', this);
	},
	updateStore: function()
	{
		var proxy = this.store.getProxy(),
			qparam = { __ffilter: [] };

		if(this.folder === null)
			qparam.__ffilter.push({
				property: 'ffid',
				operator: 'eq',
				value:    null
			});
		else
			qparam.__ffilter.push({
				property: 'ffid',
				operator: 'eq',
				value:    this.folder.getId()
			});
		// TODO: insert other search criteria here
		if(this.searchStr)
			qparam.__sstr = this.searchStr;
		proxy.extraParams = qparam;
		this.store.sort(this.sortType, this.sortDir);
	},
	renderView: function()
	{
		var me = this;

		this.fireEvent('beforerenderview', this);
		if(this.view)
		{
			this.remove(this.view, false);
			this.view = null;
		}
		if(this.viewType in this.views)
		{
			this.view = this.add(this.views[this.viewType]);
			if(this.view.refresh)
				this.view.refresh();
			return;
		}
		switch(this.viewType)
		{
			case 'icon':
				this.view = this.views[this.viewType] = this.add({
					xtype: 'fileiconview',
					region: 'center',
					getMIME: this.getMIME,
					getFileSize: Ext.bind(this.getFileSize, this),
					store: this.store,
					emptyText: this.emptyText,
					listeners: {
						selectionchange: function(dv, nodes)
						{
							this.onSelectionChange(nodes);
							if(dv.view)
								dv.view.focus();
						},
						itemdblclick: function(el, rec, item, idx, ev)
						{
							this.onFileOpen(rec, ev);
						},
						afteredit: function(ed, rec, val)
						{
							this.store.sync();
						},
						itemcontextmenu: this.onItemContextMenu,
						scope: this
					}
				});
				this.view.refresh();
				break;
			case 'list':
				this.view = this.views[this.viewType] = this.add({
					xtype: 'fileiconview',
					region: 'center',
					getMIME: this.getMIME,
					getFileSize: Ext.bind(this.getFileSize, this),
					cls: 'np-file-lview',
					useColumns: true,
					browser: this,
					iconSize: 16,
					scrollable: 'horizontal',
					store: this.store,
					emptyText: this.emptyText,
					listeners: {
						selectionchange: function(dv, nodes)
						{
							this.onSelectionChange(nodes);
							if(dv.view)
								dv.view.focus();
						},
						itemdblclick: function(el, rec, item, idx, ev)
						{
							this.onFileOpen(rec, ev);
						},
						afteredit: function(ed, rec, val)
						{
							var me = this;

							me.store.sync({
								// FIXME: Hack to make newly renamed files render properly
								callback: function(batch, opts)
								{
									me.view.refresh();
								}
							});
						},
						itemcontextmenu: this.onItemContextMenu,
						scope: this
					}
				});
				this.view.refresh();
				break;
			case 'grid':
				this.view = this.views[this.viewType] = this.add({
					xtype: 'grid',
					region: 'center',
					border: 0,
					store: this.store,
					emptyText: this.emptyText,
					allowDeselect: true,
					selModel: {
						mode: 'MULTI'
					},
					plugins: [{
						ptype: 'cellediting',
						pluginId: 'editor'
					}],
					viewConfig: {
						plugins: [{
							ptype: 'gridviewdragdrop',
							dragGroup: 'ddFile',
							dragText: this.dragText
						}]
					},
					columns: [{
						xtype: 'templatecolumn',
						tpl: new Ext.XTemplate(
							'<img class="np-block-img" src="{staticURL}/static/core/img/mime/16/{[ this.getMIME(values.mime) ]}.png" onerror=\'this.onerror = null; this.src="{staticURL}/static/core/img/mime/16/default.png"\' />',
							{
								getMIME: function(mime)
								{
									return me.getMIME(mime);
								}
							}
						),
						width: 22,
						minWidth: 22,
						maxWidth: 22,
						resizable: false,
						sortable: false,
						filterable: false,
						menuDisabled: true,
						tdCls: 'np-nopad',
						renderData: {
							baseURL: NetProfile.baseURL,
							staticURL: NetProfile.staticURL,
							xmime: this.getMIME
						}
					}, {
						text: this.gridNameText,
						dataIndex: 'fname',
						sortable: true,
						flex: 5,
						editor: {
							xtype: 'textfield',
							allowBlank: false
						}
					}, {
						text: this.gridSizeText,
						dataIndex: 'size',
						sortable: true,
						align: 'right',
						flex: 1,
						renderer: function(size)
						{
							return me.getFileSize(size);
						}
					}, {
						text: this.gridCreatedText,
						dataIndex: 'ctime',
						sortable: true,
						xtype: 'datecolumn',
						format: 'd.m.Y H:i:s',
						flex: 1
					}, {
						text: this.gridModifiedText,
						dataIndex: 'mtime',
						sortable: true,
						xtype: 'datecolumn',
						format: 'd.m.Y H:i:s',
						flex: 1
					}],
					listeners: {
						selectionchange: function(dv, nodes)
						{
							this.onSelectionChange(nodes);
						},
						itemdblclick: function(el, rec, item, idx, ev)
						{
							this.onFileOpen(rec, ev);
						},
						sortchange: function(ct, col, dir)
						{
							this.sortType = col.dataIndex;
							this.sortDir = dir;
							this.updateCheckItems(true);
							this.saveState();
							return true;
						},
						edit: function(ed, ev)
						{
							this.store.sync();
						},
						itemcontextmenu: this.onItemContextMenu,
						scope: this
					}
				});
				break;
			default:
				break;
		}
	},
	onItemContextMenu: function(el, rec, item, idx, ev)
	{
		var can_act = true,
			sel_model = this.view.getSelectionModel(),
			is_sel = sel_model.isSelected(rec),
			mi;

		ev.stopEvent();
		if(this.folder && !this.folder.get('allow_write'))
			can_act = false;
		else if(!rec.get('allow_write'))
			can_act = false;
		mi = this.ctxMenu.getComponent('del_item');
		if(mi)
			mi.setDisabled(!can_act);
		if(is_sel && (this.selectedRecords.length > 1))
			can_act = false;
		mi = this.ctxMenu.getComponent('ren_item');
		if(mi)
			mi.setDisabled(!can_act);
		if(is_sel && (this.selectedRecords.length > 1))
			can_act = false;
		else
			can_act = rec.get('allow_read');
		mi = this.ctxMenu.getComponent('dl_item');
		if(mi)
			mi.setDisabled(!can_act);
		if(is_sel && (this.selectedRecords.length > 1))
			this.ctxMenu.record = this.selectedRecords;
		else
			this.ctxMenu.record = rec;
		this.ctxMenu.showAt(ev.getXY());
		return false;
	},
	onSearchChange: function(sstr)
	{
		if(this.searchStr !== sstr)
		{
			this.searchStr = sstr;
			this.updateStore();
		}
	},
	onSelectionChange: function(nodes)
	{
		var tbar, cmp;

		this.selectedRecords = nodes;
		tbar = this.down('toolbar[dock=top]');
		if(!tbar)
			return;
		cmp = tbar.getComponent('btn_delete');
		if(cmp)
		{
			if(this.folder && !this.folder.get('allow_write'))
				cmp.setDisabled(true);
			else if(nodes.length)
			{
				var can_delete = true;

				Ext.Array.forEach(nodes, function(n)
				{
					if(!n.get('allow_write'))
						can_delete = false;
				});
				if(can_delete)
					cmp.setDisabled(false);
				else
					cmp.setDisabled(true);
			}
			else
				cmp.setDisabled(true);
		}
	},
	onFolderUpdate: function(me)
	{
		var tbar = me.down('toolbar[dock=top]'),
			btn_upload = tbar.getComponent('btn_upload');

		if(me.folder)
		{
			if(btn_upload)
			{
				if(me.folder.get('allow_write'))
					btn_upload.setDisabled(false);
				else
					btn_upload.setDisabled(true);
			}
		}
		else
		{
			if(btn_upload)
				btn_upload.setDisabled(false);
		}
	},
	onFileOpen: function(rec, ev)
	{
		// TODO: maybe signal permission denied somehow?
		if(!rec.get('allow_read'))
			return false;
		var dl = Ext.getCmp('npws_filedl');
		if(!dl)
			return false;
		dl.load({
			url: Ext.String.format(
				'{0}/core/file/dl/{1}/{2}',
				NetProfile.baseURL,
				rec.getId(), rec.get('fname')
			)
		});
		return true;
	},
	onViewChange: function(cki, checked)
	{
		if(checked && (this.viewType !== cki.itemId))
		{
			this.viewType = cki.itemId;
			this.renderView();
			this.saveState();
		}
	},
	onSortChange: function(cki, checked)
	{
		if(checked && (this.sortType !== cki.itemId))
		{
			this.sortType = cki.itemId;
			this.saveState();
			this.updateStore();
		}
	},
	onSortDirChange: function(cki, checked)
	{
		if(checked && (this.sortDir !== cki.itemId))
		{
			this.sortDir = cki.itemId;
			this.saveState();
			this.updateStore();
		}
	},
	onDragTest: function(ev)
	{
		if(!ev.dataTransfer || !ev.dataTransfer.types)
			return true;
		var bad_upload = true,
			drag_types = [
				'application/x-moz-file',
				'Files'
			];
		Ext.Array.forEach(drag_types, function(dt)
		{
			if(ev.dataTransfer.types.contains)
			{
				if(ev.dataTransfer.types.contains(dt))
					bad_upload = false;
			}
			else
			{
				if(Ext.Array.contains(ev.dataTransfer.types, dt))
					bad_upload = false;
			}
		});
		return bad_upload;
	},
	onDrop: function(e)
	{
		var ev = e.browserEvent;
		if(ev.dataTransfer && ev.dataTransfer.files)
		{
			e.stopEvent();
			this.fireEvent('filesdropped', this, ev.dataTransfer.files, e);
			return false;
		}
		return true;
	},
	getUploadParams: function()
	{
		var p = {};

		if(this.folder)
			p.ffid = this.folder.getId();
		return p;
	},
	uploadFileList: function(files)
	{
		var i, fd, param;

		if(typeof(FormData) === 'undefined')
			return false;
		if(this.folder && !this.folder.get('allow_write'))
			return false;
			// TODO: alert 'no permission'

		fd = new FormData();
		param = this.getUploadParams();
		Ext.Object.each(param, function(k, v)
		{
			fd.append(k, v);
		});
		for(i = 0; i < files.length; i++)
		{
			fd.append('file', files[i]);
		}
		this.mask(this.uploadWaitMsg);
		Ext.Ajax.request({
			url: this.uploadUrl,
			method: 'POST',
			rawData: fd,
			timeout: 300000, // 5 min, maybe dynamically adjust for large files?
			callback: function(opt, success, response)
			{
				this.unmask();
				this.updateStore();
			},
			scope: this
		});
		return true;
	},
	deleteRecords: function(recs, onyes)
	{
		var delnum, can_del = true;

		if(this.folder && !this.folder.get('allow_write'))
			return false;
		delnum = recs.length;
		Ext.Array.forEach(recs, function(r)
		{
			if(!r.get('allow_write'))
				can_del = false;
		});
		if(!can_del)
			return false;

		Ext.MessageBox.confirm(
			(delnum > 1 ? this.deleteManyTipText : this.deleteTipText),
			(delnum > 1 ? this.deleteManyMsgText : this.deleteMsgText),
			function(btn)
			{
				if(btn === 'yes')
				{
					this.store.remove(recs);
					this.store.sync();
					if(typeof(onyes) === 'function')
						onyes(recs);
				}
				return true;
			},
			this
		);
		return true;
	},
	getMIME: function(mime)
	{
		if(mime)
		{
			mime = mime.split(';')[0];
			mime = mime.split(' ')[0];
			mime = mime.replace(new RegExp('/|-', 'g'), '_');
			return mime;
		}
		return 'default';
	},
	getFileSize: function(size, factor)
	{
		var me = this,
			sz = size,
			factor = factor || 1.2,
			suffixes = [
				me.bytesText,
				me.kibText,
				me.mibText,
				me.gibText,
				me.tibText,
				me.pibText,
				me.eibText
			],
			suffix = me.bytesText,
			idx = 0;

		while(sz > (1024 * factor))
		{
			idx++;
			if(!(idx in suffixes))
				break;
			sz /= 1024;
			suffix = suffixes[idx];
		}
		sz = sz.toFixed(2);
		if(sz.substr(-3) === '.00')
			sz = sz.substr(0, sz.length - 3);
		return sz + ' ' + suffix;
	}
});

