#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from flask import Blueprint
from flask import request, render_template, url_for, make_response, jsonify
from flask import current_app as app
from geordash.api import geonetwork_subportals, get_res_details
from geordash.checks.mapstore import get_all_res
from geordash.decorators import is_superuser

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder='templates')

@admin_bp.route("/mapstore/configs")
def mapstore_configs() -> str:
    all_jobs_for_msconfigs = app.extensions['rcli'].get_taskids_by_taskname_and_args('geordash.checks.mapstore.check_configs',[])
    return render_template("admin/mapstore/configs.html", previous_configs_jobs=all_jobs_for_msconfigs, bootstrap=app.extensions["bootstrap"], showdelete=is_superuser())

@admin_bp.route("/geonetwork")
def geonetwork():
    localgn = app.extensions["conf"].get('localgn', 'urls')
    portals = geonetwork_subportals()
    if type(portals) != list:
        return make_response(jsonify({'error': f'an error occured when fetching subportals: got {portals}'}, 404))
    for p in portals:
        p['url'] = '/' + localgn + '/' + p['uuid'] + '/fre/csw'
        p['xurl'] = url_for('dashboard.csw', portal=p['uuid'])
    return render_template("admin/geonetwork.html", bootstrap=app.extensions["bootstrap"], portals=portals)

@admin_bp.route("/mapstore/maps")
def mapstore_maps():
    maps = get_all_res('MAP')
    res = list()
    for m in maps:
        d = get_res_details(request, m)
        if len(d['groups']) > 0:
            acls = '<ul>'
            for k,v in d['groups'].items():
                acls += f"<li>{k}: lecture:{v['canread']}, écriture: {v['canwrite']}</li>"
            acls += '</ul>'
        else:
            acls = "Aucune ACL ? la carte sera visible uniquement par son auteur"
        res.append({'url': m.id,
            'title': m.name,
            'owner': d['owner'],
            'acl': acls,
            'xurl': url_for('dashboard.map', mapid=m.id ),
            'viewurl': f'<a class="fa" href="/mapstore/#/viewer/{m.id}">view map {m.id}</a>'})
    all_jobs_for_ms_maps = app.extensions['rcli'].get_taskids_by_taskname_and_args('geordash.checks.mapstore.check_resources',['MAP'])
    return render_template("admin/mapstore/maps.html", bootstrap=app.extensions["bootstrap"], previous_resources_jobs=all_jobs_for_ms_maps, res=res, showdelete=is_superuser())

@admin_bp.route("/mapstore/contexts")
def mapstore_contexts():
    contexts = get_all_res('CONTEXT')
    res = list()
    for c in contexts:
        d = get_res_details(request, c)
        if len(d['groups']) > 0:
            acls = '<ul>'
            for k,v in d['groups'].items():
                acls += f"<li>{k}: lecture:{v['canread']}, écriture: {v['canwrite']}</li>"
            acls += '</ul>'
        else:
            acls = "Aucune ACL ? le contexte sera visible uniquement par son auteur"
        res.append({'url': c.id,
            'title': c.name,
            'owner': d['owner'],
            'acl': acls,
            'xurl': url_for('dashboard.ctx', ctxid=c.id ),
            'viewurl': f'<a class="fa" href="/mapstore/#/context/{c.name}">view context {c.name}</a>'})
    all_jobs_for_ms_ctxs = app.extensions['rcli'].get_taskids_by_taskname_and_args('geordash.checks.mapstore.check_resources',['CONTEXT'])
    return render_template("admin/mapstore/contexts.html", bootstrap=app.extensions["bootstrap"], previous_resources_jobs=all_jobs_for_ms_ctxs, res=res, showdelete=is_superuser())
