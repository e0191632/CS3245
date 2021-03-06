import os.path as osp
import cPickle as pickle

from utils import idf


class Dictionary(object):
    _data = {
        'terms': {},  # term format: [frequency, offset]
        'doc_ids': {}
    }
    _offset_index = {}

    def __init__(self, file_name, load=False):
        self._file_name = file_name
        if load:
            self.load()

    @property
    def _terms(self):
        return self._data['terms']

    @property
    def _doc_ids(self):
        return self._data['doc_ids']

    def add_term(self, term, offset, update_freq=True,
                 add_to_offset_index=False):
        frequency = self._terms[term][0] if term in self._terms else 0
        frequency_update_val = 1 if update_freq else 0
        self._terms[term] = (frequency + frequency_update_val, offset)
        if add_to_offset_index:
            self._offset_index[offset] = term

    def add_doc_id(self, doc_id, length):
        self._doc_ids[doc_id] = length

    def generate_idf(self, n):
        for term, (frequency, offset) in self._terms.iteritems():
            self._terms[term] = (idf(frequency, n), offset)

    def term_for_offset(self, offset):
        return self._offset_index.get(offset, None)

    def term(self, term):
        return self._terms.get(term, (None, None))

    def terms(self):
        return self._terms.iteritems()

    def doc_length(self, doc_id):
        return self._doc_ids.get(doc_id, None)

    def does_term_exist(self, term):
        return term in self._terms

    def save(self):
        with open(self._file_name, 'w') as f:
            pickle.dump(self._data, f, pickle.HIGHEST_PROTOCOL)

    def load(self):
        if not osp.exists(self._file_name):
            return False
        with open(self._file_name) as f:
            self._data = pickle.load(f)
        return True
