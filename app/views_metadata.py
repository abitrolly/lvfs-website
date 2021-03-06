#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018 Richard Hughes <richard@hughsie.com>
# Licensed under the GNU General Public License Version 2

import humanize

from flask import render_template, g, make_response, flash, redirect, url_for
from flask_login import login_required

from app import app, db

from .models import Vendor, Remote
from .util import _error_internal, _error_permission_denied

@app.route('/lvfs/metadata/<group_id>')
@login_required
def metadata_remote(group_id):
    """
    Generate a remote file for a given QA group.
    """

    # find the vendor
    vendor = db.session.query(Vendor).filter(Vendor.group_id == group_id).first()
    if not vendor:
        return _error_internal('No vendor with that name')

    # security check
    if not vendor.check_acl('@view-metadata'):
        return _error_permission_denied('Unable to view metadata')

    # generate file
    remote = []
    remote.append('[fwupd Remote]')
    remote.append('Enabled=true')
    remote.append('Title=Embargoed for ' + group_id)
    remote.append('Keyring=gpg')
    remote.append('MetadataURI=https://fwupd.org/downloads/%s' % vendor.remote.filename)
    remote.append('OrderBefore=lvfs,fwupd')
    fn = group_id + '-embargo.conf'
    response = make_response('\n'.join(remote))
    response.headers['Content-Disposition'] = 'attachment; filename=' + fn
    response.mimetype = 'text/plain'
    return response

@app.route('/lvfs/metadata')
@login_required
def metadata_view():
    """
    Show all metadata available to this user.
    """

    # show all embargo metadata URLs when admin user
    vendors = []
    for vendor in db.session.query(Vendor).\
                    filter(Vendor.is_account_holder != 'no').all():
        if vendor.check_acl('@view-metadata'):
            vendors.append(vendor)
    remotes = {}
    for r in db.session.query(Remote).all():
        remotes[r.name] = r
    return render_template('metadata.html', vendors=vendors, remotes=remotes)

@app.route('/lvfs/metadata/rebuild')
@login_required
def metadata_rebuild():
    """
    Forces a rebuild of all metadata.
    """

    # security check
    if not g.user.check_acl('@admin'):
        return _error_permission_denied('Only admin is allowed to force-rebuild metadata')

    # update metadata
    scheduled_signing = None
    for r in db.session.query(Remote).filter(Remote.is_public).all():
        r.is_dirty = True
        if not scheduled_signing:
            scheduled_signing = r.scheduled_signing
    for vendor in db.session.query(Vendor).\
                    filter(Vendor.is_account_holder != 'no').all():
        vendor.remote.is_dirty = True
    if scheduled_signing:
        flash('Metadata will be rebuilt %s' % humanize.naturaltime(scheduled_signing), 'info')
    return redirect(url_for('.metadata_view'))
