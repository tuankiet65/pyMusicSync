#!/usr/bin/env python3
import re


class ModifierRule:
    def __init__(self, field, match, replaceWith):
        self.field = field
        self.match = re.compile(match)
        self.replaceWith = replaceWith

    def apply(self, metadata):
        tmpMtd = metadata
        self.match.sub(self.replaceWith, tmpMtd[self.field])
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
