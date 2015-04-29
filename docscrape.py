#!/usr/bin/env python2

"""DocScrape — bootscrap contact info about professionals through web scraping"""

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import click
import json
import csv
import itertools
import re
from collections import defaultdict
import Levenshtein

def listify(item):
    if type(item) in [list, tuple, set, dict]:
        return(item)
    else:
        return([item])

def build_mappings(map_filename):
    separators = ["", " ", "-", "_", "/"]
    mappings = defaultdict("Other")
    non_sep = re.compile(r"[a-zA-Z]")
    
    with open(map_filename, 'r', encoding="utf-8") as map_file:
        map_spec = json.load(map_file)
    for field, spec_set in map_spec.items():
        for spec in spec_set:
            if type(spec) in [str, unicode]:
                mappings[spec] = field
            else:
                for variant in itertools.product(*[listify(item)
                                                   for item in spec]):
                    for sep in separators:
                        sep_variant = sep.join(variant)
                        if non_sep.match(sep_variant):
                            mappings[sep_variant] = field
    return(mappings)

def map_record(record, mappings):
    mapped_record = defaultdict(list)
    for field, value in record.items():
        mapped_record[mappings[field]].append(value)
    return(mapped_record)

def import_data(filename, mappings):
    with open(filename, 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        data = [map_record(record, mappings) for record in reader]
        return(data)

