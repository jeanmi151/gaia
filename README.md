# geOrchestra dashboard

this project aims at providing a user-centric dashboard for [geOrchestra](https://georchestra.org):
- for admins, showing inconsistencies/errors in the datasets/maps, reusing what
  was done in [sdi-consistency-check](https://github.com/georchestra/sdi-consistence-check/)
- for users, direct links to:
  - what they can access
  - what they can do (depending on their rights/roles)
  - list their md/data
  - list their org md

one of the goal is to provide an api returning JSON so that it can be reused in
other components/webpages (such as the [ids
homepage](https://github.com/georchestra/htdocs/))

it is a work in progress, being developed when spare time is available. for now
developped in my own github account, but if enough features are developed and
interest is shown, it'll move to the
[geOrchestra](https://github.com/georchestra/) organization.

## dependencies

written using the versions of python/flask/celery provided by debian 12, it
should only require 'recent' versions of those:

```
apt install python3-flask-bootstrap python3-flask python3-celery
```

## integration

the web service should be added behind geOrchestra's security-proxy/gateway, so
that it knows the connected user and can display user-tailored information.

add this line to `/etc/georchestra/security-proxy/target-mappings.properties`:
```
dashboard=http://<hostname>:<port>/dashboard/
```

and visit https://<idsurl>/dashboard/home, which should list for now:
- your metadatas
- the maps & contexts you can access

## service

needs two services running (TODO)
- the flask webapp, accessed at https://<idsurl>/dashboard/
- the celery worker, for long-running checks

for now during development those are started by [`run.sh`](run.sh), proper
integration via gunicorn/systemd is the goal

## configuration

for now a redis instance is used for celery's broker/result backend storage, to
configure in [`config.py`](config.py.example) - celery can use rabbitmq for the
broker, and in the end the geOrchestra PostgreSQL database will be used to
store task results.

it tries as much as possible to autoconfigure itself by reading configuration
files from [geOrchestra's datadir](https://github.com/georchestra/datadir)
