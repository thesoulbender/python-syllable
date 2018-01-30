# coding=utf-8
""" An encoder which learns byte pair encodings for white-space separated text.  Can tokenize, encode, and decode. """
from collections import Counter

try:
    from typing import Dict, Iterable, Callable, List, Any, Iterator
    import string, pickle, os, pkg_resources, unidecode
except ImportError:
    pass

supported_languages = ["tr"]

class Encoder:
    def __init__(self, lang="tr", limitby=None, limit=0):
        #
        # lang: language for syllable encoder
        # limitby: limit type to be used for allowing syllables ("vocabulary", "percentile", "count")
        # limit: limiting factor (
        #    vocabulary: max size of distinct syllables, 
        #    percentile:[0-1], 
        #    count: min occurance of syllable in corpus)
        #
        self.lang = lang
        self.limitby = limitby
        self.limit = limit
        self.special_chars = {}
        self.unicode_char_mapping = {}
        if self.lang not in supported_languages:
            raise Exception('Language not supported: '+lang)
        
        self.vowels = "aeiouAEIOU"
        self.vowel_map = [False for i in range(256)]
        for c in self.vowels:
            self.vowel_map[ord(c)] = True
        self.load_package_vec()
        
    def is_vowel(self, c):
        if c not in self.special_chars:
            if c in self.unicode_char_mapping:
                return self.vowel_map[ord(self.unicode_char_mapping[c])]
            else:
                c_ = unidecode.unidecode(c)
                self.unicode_char_mapping[c] = c_
                if len(c_)==1:
                    return self.vowel_map[ord(c_)]
                else:
                    self.special_chars[c] = c_
                    return False
        return False
    
    def char_is_special(self, c):
        return c in string.punctuation or c in self.special_chars
    
    def has_vowel(self, text):
        for c in text:
            if self.is_vowel(c):
                return True
        return False
    
    def should_return_syllable(self, syllable):
        if self.limitby == None:
            return True
        elif syllable not in self.vocab:
            return False
        elif self.limitby == "vocabulary":
            return self.vocab[syllable]["rank"]<self.limit
        elif self.limitby == "percentile":
            return self.vocab[syllable]["percentile"]<self.limit
        elif self.limitby == "count":
            return self.vocab[syllable]["count"]>self.limit
        else:
            raise Exception('Unsupported limit type: '+self.limitby)
    
    def decode_word(self, word):
        vowel = [self.is_vowel(c) for c in word]
        last_ind = 0
        for i,c in enumerate(vowel):
            if self.char_is_special(word[i]):
                if last_ind<i:
                    yield word[last_ind:i]
                yield word[i]
                last_ind = i+1
            elif i==0:
                continue
            elif last_ind == i:
                continue
            elif c and vowel[i-1]:
                yield word[last_ind:i]
                last_ind = i
            elif c and not vowel[i-1] and last_ind<i-1:
                str_ = word[last_ind:i-1]
                if self.has_vowel(str_):
                    yield str_
                    last_ind = i-1
                else:
                    continue
            elif c and not vowel[i-1] and last_ind>=i-1:
                continue
            elif not c and vowel[i-1]:
                continue
            else:
                continue
        if last_ind<len(word):
            yield word[last_ind:]
    
    def decode(self, text):
        words = text.split()
        for w in words:
            try:
                yield list(self.decode_word(w))
            except:
                print("Error with word: "+w)
            
        
    def fit(self,corpus):
        self.vocab = {}
        for sentence in corpus:
            for ws in self.decode(sentence):
                for syllable in ws:
                    if syllable not in self.vocab:
                        self.vocab[syllable] = {"count":1}
                    else:
                        self.vocab[syllable]["count"] += 1
        self.process_vocab()
        self.save_vec()
    
    def process_vocab(self):
        sorted_vocab = sorted(self.vocab.items(), key=lambda x: x[1]["count"], reverse=True)
        total = 0
        for s in sorted_vocab:
            total += s[1]["count"]
        running_sum = 0
        rank = 1
        for s in sorted_vocab:
            s[1]["percentile"] = running_sum/total
            s[1]["rank"] = rank
            rank += 1
            running_sum += s[1]["count"]
    
    def save_vec(self, path="./"):
        with open(path+self.lang, 'wb') as handle:
            pickle.dump(self.vocab, handle, protocol=pickle.HIGHEST_PROTOCOL)
            
    def load_vec(self, path="./"):
        with open(path+self.lang, 'rb') as handle:
            self.vocab = pickle.load(handle)
            self.process_vocab()

    def load_package_vec(self):
        s = pkg_resources.resource_string("syllable",os.path.join("vectors",self.lang))
        self.vocab = pickle.loads(s)
