import spacy
from functools import cache

@cache
def modele():
    return spacy.load("fr_core_news_sm", exclude=["ner"])
