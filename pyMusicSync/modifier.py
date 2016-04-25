#!/usr/bin/env python3
import re


class ModifierRule:
    def __init__(self, field, match, replaceWith):
    	self.field=field
    	self.match=re.compile(match)
    	self.replaceWith=replaceWith
    	
    def apply(self, metadata):
    	tmpMtd=metadata
    	self.match.sub(self.replaceWith, tmpMtd[self.field])
    	return tmpMtd


class Modifier:

	modifiers=[]
    def __init__(self):
        pass
        
    def addModifierRule(self, field, match, replaceWith):
    	self.mofifiers.append(ModifierRule(field, match, replaceWith))
    
    def apply(self, metadata):
    	for modifier in modifiers:
    		metadata=modifier.apply(metadata)