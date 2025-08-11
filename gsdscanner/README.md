# gsdscanner

This is a geoserver datadir parser, which tries to gather as much info as
possible from the contents of the datadir, in order to check for the datadir
consistency. It uses information from the internal XML files, and the
geospatial datas found in the datadir.

It is more or less a python port from a [previous
project](https://github.com/landryb/geoserver-datadir-checker/).

## item types

### `workspace`

### `coveragestore`
store for raster datas, analysis currently supports:
- `GeoTIFF`
- `ImageMosaic`

### `datastore`
store for vector datas, analysis currently supports:
- `Shapefile`
- `Directory of shapfiles`
- `Geopackage`
- `Postgis (JNDI)`

plain postgis not supported since we can't decrypt hashed passwords.. _postgis
(JNDI)_ only works if the JNDI information can be retrieved from the tomcat
configuration files.

### `coverage`
intermediary object between `coveragestore` and `layer`

### `featuretype`
intermediary object between `datastore` and `layer`

### `layer`
links a `layer` with its `style`s. a geoserver `layer` consists of a `layer`
object tied to a `coverage` or a `featuretype`, depending if it is a _RASTER_
layer or _VECTOR_ layer.

### `style`
describes a `style` object, currently only SLD is supported.

### `VectorData`
analyses a `Shapefile` or a `Geopackage` found in the `data/` subdir.

### `RasterData`
analyses `TIFF` files found in the `data/` subdir.

### `SLD`
parses an SLD and tries to analyse its first rule title.

## requirements

the process running the checks needs to be able to read the _geoserver
datadir_, as well as the `conf/server.xml` tomcat configuration file. use the
right unix user, or give the user the right group membership.

## checks

the checks are done by a [celery task](../geordash/checks/gsd.py) checking each
object for each category.

## running standalone

the [checkgsd.py](../checkgsd.py) script at the toplevel of the repository can be
run standalone (eg outside of gaia/georchestra), pointing at the path of a
given datadir.
