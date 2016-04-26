#!/usr/bin/env python3
import re
import logging

class ModifierRule:
    def __init__(self, field, match, replaceWith):
        self.field = field
        self.match = re.compile(match)
        self.replaceWith = replaceWith

    def apply(self, metadata):
        tmpMtd = metadata
        tmpValue = getattr(metadata, self.field)
        setattr(tmpMtd, self.field, self.match.sub(self.replaceWith, tmpValue))
        if getattr(tmpMtd, self.field) != tmpValue:
            logging.debug("replacing field {} from {} to {}".format(self.field, tmpValue, tmpMtd))
        return tmpMtd


class Modifier:
    modifiers = []

    def __init__(self, modifierRules=None):
        if modifierRules is None:
            modifierRules = []
        for rules in modifierRules:
            self.addRule(**rules)
        pass

    def addRule(self, field, match, replaceWith):
        self.modifiers.append(ModifierRule(field, match, replaceWith))

    def apply(self, metadata):
        for modifier in self.modifiers:
            metadata = modifier.apply(metadata)
        return metadata
