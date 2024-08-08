#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from configparser import ConfigParser
from itertools import chain
import json

class GeorchestraConfig:
    def __init__(self):
        self.sections = dict()
        parser = ConfigParser()
        with open("/etc/georchestra/default.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections['default'] = parser['section']
        with open("/etc/georchestra/mapstore/geostore.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections['mapstoregeostore'] = parser['section']
        with open("/etc/georchestra/security-proxy/targets-mapping.properties") as lines:
            lines = chain(("[section]",), lines)  # This line does the trick.
            parser.read_file(lines)
        self.sections['secproxytargets'] = parser['section']
        self.sections['urls'] = dict()
        with open("/etc/georchestra/mapstore/configs/localConfig.json") as file:
            s = file.read()
            localconfig = json.loads(s)
            # used to find geonetwork entry in sec-proxy targets
            try:
                localentry = localconfig["initialState"]["defaultState"]["catalog"]["default"]["services"]["local"]
                self.sections['urls']['localgn'] = localentry['url'].split('/')[1]
            except:
                # safe default value
                self.sections['urls']['localgn'] = 'geonetwork'
            try:
                localentry = localconfig["initialState"]["defaultState"]["catalog"]["default"]["services"]["localgs"]
                self.sections['urls']['localgs'] = localentry['url'].split('/')[1]
            except:
                # safe default value
                self.sections['urls']['localgs'] = 'geoserver'

    def get(self, key, section='default'):
        if section in self.sections:
            return self.sections[section].get(key, None)
        else:
            return None
