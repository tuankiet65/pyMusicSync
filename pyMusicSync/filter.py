#!/usr/bin/env python3

# A simple (right?) filter
# Only supports AND (aka all FilterRule must return True)

import re


class FilterRule:
    def __init__(self, field, operator, value):
        self.field = field
        self.operator = operator
        if self.operator == "regex":
            self.value = re.compile(value)
        else:
            self.value = value

    def execute(self, metadata):
        if self.operator == "regex":
            if re.search(self.value, metadata[self.field]) is None:
                return False
            else:
                return True
        elif self.operator == "<=":
            return metadata[self.field] <= self.value
        else:
            raise NotImplementedError


class Filter:
    rules = []

    def __init__(self):
        pass

    def addRule(self, field, operator, value):
        self.rules.append(FilterRule(field, operator, value))

    def execute(self, metadata):
        for rule in self.rules:
            if not rule.execute(metadata):
                return False
        return True
