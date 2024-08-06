#!/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

from configparser import ConfigParser
from itertools import chain

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

    def get(self, key, section='default'):
        if section in self.sections:
            return self.sections[section].get(key, None)
        else:
            return None
