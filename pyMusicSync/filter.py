#!/usr/bin/env python3

# A simple (right?) filter
# Only supports AND (aka all FilterRule must return True)

import re
import logging


class FilterRule:
    def __init__(self, field, operator, value, applyNot=False):
        self.field = field
        self.operator = operator
        if self.operator == "regex":
            self.value = re.compile(value)
        else:
            self.value = value
        self.applyNot = applyNot

    def apply(self, metadata):
        fieldValue = getattr(metadata, self.field)
        if self.operator == "regex":
            if re.search(self.value, fieldValue) is None:
                return False ^ self.applyNot
            else:
                return True ^ self.applyNot
        elif self.operator == "<=":
            return (fieldValue <= self.value) ^ self.applyNot
        elif self.operator == "==":
            return (fieldValue == self.value) ^ self.applyNot
        else:
            raise NotImplementedError("Unimplemented operator: {}".format(self.operator))


class Filter:
    rules = []

    def __init__(self, filterRules=None):
        if filterRules is None:
            filterRules = []
        for rule in filterRules:
            self.addRule(**rule)
        pass

    def addRule(self, field, operator, value, applyNot=False):
        self.rules.append(FilterRule(field, operator, value, applyNot))

    def check(self, metadata):
        for rule in self.rules:
            if not rule.apply(metadata):
                return False
        return True
