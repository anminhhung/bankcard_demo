from Levenshtein import *
import codecs
import unidecode
from preprocess import LIST_FIRSTNAME_PREPROCESS, LIST_MIDNAME_PREPROCESS

with open("my_dict/bank.txt") as f:
    content = f.readlines()
LIST_BANK_DEF = [x.strip() for x in content] 

with open("my_dict/type_card.txt") as f:
    content = f.readlines()
LIST_TYPE_CARD_DEF = [x.strip() for x in content] 

def typecardMatch(raw_input):
	# raw_input = raw_input.upper()
	index_min = max(range(len(LIST_TYPE_CARD_DEF)), \
		key=lambda x: ratio(raw_input, LIST_TYPE_CARD_DEF[x]))
	return LIST_TYPE_CARD_DEF[index_min] if distance(raw_input, LIST_TYPE_CARD_DEF[index_min]) < 2 else None

def bankMatch(raw_input):
	# raw_input = raw_input.upper()
	index_min = max(range(len(LIST_BANK_DEF)), \
		key=lambda x: ratio(raw_input, LIST_BANK_DEF[x]))
	return LIST_BANK_DEF[index_min] if distance(raw_input, LIST_BANK_DEF[index_min]) < 7 else None

def firstnameMatch(raw_input):
	index_min = max(range(len(LIST_FIRSTNAME_PREPROCESS)), \
		key=lambda x: ratio(raw_input, LIST_FIRSTNAME_PREPROCESS[x]))
	return LIST_FIRSTNAME_PREPROCESS[index_min] if distance(raw_input, LIST_FIRSTNAME_PREPROCESS[index_min]) < 2 else None

def midnameMatch(raw_input):
	index_min = max(range(len(LIST_MIDNAME_PREPROCESS)), \
		key=lambda x: ratio(raw_input, LIST_MIDNAME_PREPROCESS[x]))
	return LIST_MIDNAME_PREPROCESS[index_min] if distance(raw_input, LIST_MIDNAME_PREPROCESS[index_min]) < 2 else None