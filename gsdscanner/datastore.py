#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from lxml import etree
from geordash.utils import getelemat
import os


class Datastore(dict):
    def __init__(self, xmlf):
        self.file = xmlf
        self.schema = None
        self.dbtype = None

    def __repr__(self):
        return f"Datastore: file={self.file}, id={self.id}, name={self.name}, type={self.type}, workspaceid={self.workspaceid}"

    def parse(self):
        xml = etree.parse(self.file)
        self.id = getelemat(xml, "/dataStore/id")
        self.name = getelemat(xml, "/dataStore/name")
        self.type = getelemat(xml, "/dataStore/type")
        self.enabled = getelemat(xml, "/dataStore/enabled")
        self.workspaceid = getelemat(xml, "/dataStore/workspace/id")
        # can be none
        self.connurl = getelemat(
            xml, '/dataStore/connectionParameters/entry[@key="url"]'
        )
        # probably postgis or geopackage
        if self.connurl is None and "shapefile" not in self.type.lower():
            self.dbtype = getelemat(
                xml, '/dataStore/connectionParameters/entry[@key="dbtype"]'
            )
            if self.dbtype == "geopkg":
                self.connurl = getelemat(
                    xml, '/dataStore/connectionParameters/entry[@key="database"]'
                )
            elif self.dbtype == "postgis" and "JNDI" in self.type:
                self.connurl = getelemat(
                    xml,
                    '/dataStore/connectionParameters/entry[@key="jndiReferenceName"]',
                )
                self.schema = getelemat(
                    xml, '/dataStore/connectionParameters/entry[@key="schema"]'
                )
        if self.connurl and not self.connurl.startswith('java:'):
            # drop scheme prefix, and prepend basedir (extracted from self.file) if relative path
            path = self.connurl.removeprefix('file:')
            if not os.path.isabs(path):
                idx = self.file.find("workspaces")
                path = self.file[0:idx] + path
            self.connurl = path
        # if type = PostGIS (JNDI) look for name matching connurl java:comp/env/ in tomcat's conf/server.xml
        # and list tables in the given database
