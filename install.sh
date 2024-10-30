if [ "$(id -u)" -ne 0 ] ; then
	echo "run me as root"
	exit 1
fi
set -e
WORKDIR=$(pwd)
grep -q gaia /etc/group || groupadd gaia
for f in celery gunicorn ; do
	grep -q $f /etc/passwd || useradd -r -g gaia ${f}
	sed -e "s#WORKDIR#${WORKDIR}#" systemd/gaia-${f}.service.in > /etc/systemd/system/gaia-${f}.service
done
install -d $WORKDIR/workdir -o celery
systemctl daemon-reload
