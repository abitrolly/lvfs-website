#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Richard Hughes <richard@hughsie.com>
# Licensed under the GNU General Public License Version 2

import os
import sys
import boto3

from flask import session, request, flash, render_template

from app import app, db

from .affidavit import Affidavit

def _create_affidavit():
    """ Create an affidavit that can be used to sign files """
    key_uid = db.users.get_signing_uid()
    return Affidavit(key_uid, app.config['KEYRING_DIR'])

def _upload_to_cdn(fn, blob):
    """ Upload something to the CDN """
    if not app.config['CDN_BUCKET']:
        return
    key = os.path.join("downloads/", os.path.basename(fn))
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(app.config['CDN_BUCKET'])
    bucket.Acl().put(ACL='public-read')
    print "uploading %s as %s" % (fn, key)
    obj = bucket.put_object(Key=key, Body=blob)
    obj.Acl().put(ACL='public-read')

def _get_client_address():
    """ Gets user IP address """
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    return request.remote_addr

def _event_log(msg, is_important=False):
    """ Adds an item to the event log """
    username = None
    qa_group = None
    if 'username' in session:
        username = session['username']
    if not username:
        username = 'anonymous'
    if 'qa_group' in session:
        qa_group = session['qa_group']
    if not qa_group:
        qa_group = 'admin'
    db.eventlog.add(msg, username, qa_group,
                    _get_client_address(), is_important)

def _error_internal(msg=None, errcode=402):
    """ Error handler: Internal """
    _event_log("Internal error: %s" % msg, is_important=True)
    flash("Internal error: %s" % msg)
    return render_template('error.html'), errcode

def _error_permission_denied(msg=None):
    """ Error handler: Permission Denied """
    _event_log("Permission denied: %s" % msg, is_important=True)
    flash("Permission denied: %s" % msg)
    return render_template('error.html'), 401

def main():
    if len(sys.argv) != 2:
        print "usage: filename"
        return
    blob = open(sys.argv[1], 'rb').read()
    _upload_to_cdn(sys.argv[1], blob)

if __name__ == "__main__":
    main()
