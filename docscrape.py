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

MATCH_STRENGTH = 0.75 # Confidence threshold (out of 1.0)

def listify(item):
    if type(item) in [list, tuple, set, dict]:
        return(item)
    else:
        return([item])

def build_mappings(map_filename):
    """Build mappings of data fields to various field names from
    mapping specifications."""
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
    """Convert field names of a given record to the standardized form."""
    mapped_record = defaultdict(list)
    for field, value in record.items():
        mapped_record[mappings[field]].append(value)
    return(mapped_record)

def import_data(filename, mappings):
    """Collect data from a CSV file and bind it as a list of dictionaries."""
    with open(filename, 'rb') as csvfile:
        reader = csv.DictReader(csvfile)
        data = [map_record(record, mappings) for record in reader]
        return(data)

def import_sources(sources_file):
    """Collect per source scraping instructions."""
    with open(sources_file, "r", encoding="utf-8") as sourcefile:
        return(json.load(sourcefile))

def do_step(driver, record, step, mappings, result=None):
    """Process the specified step."""
    if step.has_key["with result"] and step["with result"] and result:
        result.find_element(getattr(By, step["element"][0]),
                            step["element"][1])
    else:
        element = driver.find_element(getattr(By, step["element"][0]),
                                      step["element"][1])
    if step["action"][0] == "data":
        pass
    else:
        getattr(element, step["action"][0])

def check_result(driver, record, result, criteria, mappings):
    """Check the provided result for a match to the record."""
    if not criteria[0].has_key("weight"):
        weight_steps = map(float, range(1, len(criteria)+1))
        weights = [step/sum(weight_steps) for step in weight_steps]
        for criterion in criteria:
            criterion["weight"] = weights.pop()
    score = 0
    for criterion in criteria:
        element = result.find_element(getattr(By, criterion["element"][0]),
                                      criterion["element"][1])
        if getattr(element, criterion["test"][0])(
                criterion["test"][1].format(**record)):
            score += criterion["weight"]
    return(score)

def bootstrap(driver, record, sources, mappings):
    """Scrape each source for more data for the provided record."""
    for source in sources:
        driver.get(source["address"])
        if source.has_key("steps"):
            for step in source["steps"]:
                do_step(driver, record, step, mappings)
        if source.has_key("results"):
            for result in driver.find_elements(
                    getattr(By, source["results"]["element"][0]),
                    source["results"]["element"][1]):
                if check_result(driver, record, result,
                                source["results"]["criteria"],
                                mappings) > MATCH_STRENGTH:
                    if source.has_key("match") and \
                       source["match"].has_key("steps"):
                        for step in source["match"]["steps"]:
                            if step.has_key("with result") and \
                               step["with result"]:
                                do_step(driver, record, step,
                                        mappings, result)
                            else:
                                do_step(driver, record, step, mappings)
                        break

@click.command()
@click.option("--mapping-file", "-m", default="field-mapping.json",
              help="path to field-mapping file")
@click.option("--sources-file", "-s", default="sources.json",
              help="path to source instructions")
@click.argument("input_file")
def main(mapping_file, sources_file, input_file):
    mappings = build_mappings(mapping_file)
    sources = import_sources(sources_file)
    data = import_data(input_file, mappings)
    driver = webdriver.Chrome()
    driver.implicitly_wait(10)
    for record in data:
        bootstrap(driver, record, sources, mappings)
