find geordash/templates/ -type f | while read f;  do echo $f ; python3 tests/check_jinja.py $f ; done
