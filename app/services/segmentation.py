import pysbd
import re

def segment(texte: str) -> list[list[str]]:
    seg = pysbd.Segmenter(language="fr", clean=False)
    segmented = re.split(r"\n{2,}", texte) #sépare le texte en paragraphes s'il y a plus de deux retours à la ligne
    filtered = []
    
    for s in segmented:                    #sépare les paragraphes en phrases et retourne une liste
        if s.strip():
            phrases = seg.segment(s)
            filtered.append(phrases)
    return filtered