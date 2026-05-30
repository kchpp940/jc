#!/usr/bin/env python3
# Shared utilities for jc document generation scripts
from jinja2 import Environment, FileSystemLoader
from jc.lib import __release__


def jinja_env():
    return Environment(loader=FileSystemLoader('templates'))


def release():
    return __release__
