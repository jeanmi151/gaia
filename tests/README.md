# testing

so far the tests are written with my dev instance as a target, some work
required to use a public demo instance or proper ad-hoc instances with fixtures ?
in all cases, i dont plan to rely on docker for that..

## check jinja syntax

`check_jinja_syntax.sh` ensures that all jinja templates syntax is valid

## pytest

either `pytest` or `python3 -m pytest` or `python3 tests/test_xxx.py` should work.

one can use `pytest --log-cli-level 4` to see debug output from functions
(cf the [pytest doc on live logs](https://docs.pytest.org/en/stable/how-to/logging.html#live-logs))
