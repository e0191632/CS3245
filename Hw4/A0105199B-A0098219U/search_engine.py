import math
import cPickle
import heapq
import urllib
import urllib2
from dictionary import Dictionary
from postings import Postings
from utils import tf
from ipc import IPCIndex
from trie import Trie
import copy

class IPCEngine(object):
    """
    Search engine that uses IPC classification to retrieve patents
    """

    def __init__(self):
        self.ipc_index = IPCIndex('ipc_index.txt')
        self.trie = Trie()

    def execute_query(self, query_map):
        ipc_codes = []
        # make a set of all IPC codes for each query term
        for qw in query_map:
            ipc_codes.extend(self.ipc_index.get(qw))
            ipc_codes = list(set(ipc_codes))

        results = set([])

        # search for the IPC codes in the trie of patents sorted by IPC codes
        for ipc_code in ipc_codes:
            files = self.trie.getfiles(ipc_code)
            results.update(files)

        results = list(results)
        results = map(lambda x: x[:-4], results)
        return " ".join([str(x) for x in results])


class NotAHackEngine(object):
    """
    Search engine that uses a web service to retrieve patents
    """

    def __init__(self):
        with open('class_index.txt') as fin:
            self.index = cPickle.load(fin)

    def execute_query(self, query):
        # encode the query in the server request
        url_encoded = urllib.urlencode({'text': query})
        magic_numbers = urllib2.urlopen(
            'http://karankamath.com:8080/get_results?' + url_encoded).read()

        if magic_numbers.strip() == 'error':
            return ""

        # get the IPC classes for the query submitted to the server
        pairs = magic_numbers.split(',')
        pairs = [p.split() for p in pairs]
        classnames = [p[0] for p in pairs]

        outputset = set()
        output = []

        #get all the docs that have the specific IPC class
        for cname in classnames:
            for doc in self.index.get(cname, []):
                if doc not in outputset:
                    output.append(doc)
                    outputset.add(doc)
        return " ".join(output)

class Engine(object):
    """
    Search engine that uses a simple vector space model to retrieve patents
    """

    NUM_RESULTS = 500

    def __init__(self, fd, fp):
        self.dictionary = Dictionary(fd, load=True)
        self.postings = Postings(fp, mode='r')

    def _get_postings(self, offset):
        """
        This method gets the postings list at an offset
        """
        return self.postings.list_at_offset(offset)

    def _accumulate_scores(self, scores, postings_list, q_wt):
        """
        This method accumulates scores for a term
        """
        for doc_id, d_tf in postings_list:
            scores[doc_id] = scores.get(doc_id, 0) + q_wt * d_tf

    def _normalize(self, scores, q_len):
        """
        This method normalises scores for every document
        """
        for doc_id in scores:
            scores[doc_id] /= (q_len * self.dictionary.doc_length(doc_id))

    def _get_top_n_docs(self, scores, n):
        """
        This method creates a heap of the docs and pick out the top few
        """
        scores_heap = [(-v, k) for k, v in scores.items()]
        heapq.heapify(scores_heap)
        return [heapq.heappop(scores_heap)[1] for i in xrange(n)
                if len(scores_heap) > 0]

    def execute_query(self, query_map):
        """
        This method is called to execute a query
        """
        scores = {}
        for term in query_map:
            q_idf, term_offset = self.dictionary.term(term)

            # unknown term, skip everything, score 0
            if term_offset is None:
                continue

            # accumulate scores for postings list
            query_map[term] = q_wt = tf(query_map[term]) * q_idf
            postings_list = self._get_postings(term_offset)
            self._accumulate_scores(scores, postings_list, q_wt)

        # perform length normalization (query and document)
        q_len = math.sqrt(sum(x * x for x in query_map.values()))
        self._normalize(scores, q_len)

        # find top n
        # top_n_docs = self._get_top_n_docs(scores, Engine.NUM_RESULTS)
        # return " ".join(str(x) for x in top_n_docs)

        return " ".join(str(x) for x in scores.keys())

class feedbackEngine(object):
    """
    Search engine that uses relevance feedback
    with a vector space model to retrieve patents
    """

    global NUM_RESULTS
    global QUERY_WEIGHT
    global P_FEEDBACK_WEIGHT
    NUM_RESULTS = 10
    QUERY_WEIGHT = 0.5
    P_FEEDBACK_WEIGHT = 0.5

    def __init__(self, fd, fp):
        self.dictionary = Dictionary(fd, load=True)
        self.postings = Postings(fp, mode='r')
        self.feedback = False

    def _get_postings(self, offset):
        """
        This method gets the postings list at an offset
        """
        return self.postings.list_at_offset(offset)

    def _accumulate_scores(self, scores, postings_list, q_wt):
        """
        This method accumulates scores for a term
        """
        for doc_id, d_tf in postings_list:
            scores[doc_id] = scores.get(doc_id, 0) + q_wt * d_tf

    def _normalize(self, scores, q_len):
        """
        This method normalises scores for every document
        """
        for doc_id in scores:
            scores[doc_id] /= (q_len * self.dictionary.doc_length(doc_id))

    def _get_top_n_docs(self, scores, n):
        """
        This method creates a heap of the docs and pick out the top few
        """
        scores_heap = [(-v, k) for k, v in scores.items()]
        heapq.heapify(scores_heap)
        return [heapq.heappop(scores_heap)[1] for i in xrange(n)
                if len(scores_heap) > 0]

    def relevance_feedback(self, query_map, top_n_docs):
        """
        This method expands the query based on pseudo relevance feedback
        """
        self.feedback = True
        vector_sum = {}
        term_dict = self.dictionary._terms

        # constructing the document vector for the top n docs
        for term in term_dict:
            term_offset = term_dict[term][1]

            # unknown term, skip everything, score 0
            if term_offset is None or term is None:
                continue

            # adding the term frequencies of all the documents in top_n_docs
            postings_list = self._get_postings(term_offset)
            for doc_id, d_tf in postings_list:
                if doc_id in top_n_docs:
                    temp_term_freq = d_tf*P_FEEDBACK_WEIGHT
                    if term in vector_sum:
                        vector_sum[term] += temp_term_freq
                    else:
                        vector_sum[term] = temp_term_freq

        # averaging the vector for the top docs to get the centroid
        for term in vector_sum:
            vector_sum[term] /= NUM_RESULTS
            vector_sum[term] *= P_FEEDBACK_WEIGHT

        # adding the initial query vector terms to the centroid
        for term in vector_sum:
            if term in query_map:
                vector_sum[term] += query_map[term] * QUERY_WEIGHT

        # adding the remaining terms left in the query vector
        for term in query_map:
            if term not in vector_sum:
                vector_sum[term] = query_map[term] * QUERY_WEIGHT

        # execute query with the new query vector
        return self.execute_query(vector_sum)

    def execute_query(self, query_map):
        """
        This method is called to execute a query
        """
        scores = {}
        query_map_copy = copy.deepcopy(query_map)
        for term in query_map:
            q_idf, term_offset = self.dictionary.term(term)

            # unknown term, skip everything, score 0
            if term_offset is None:
                continue

            # accumulate scores for postings list
            query_map[term] = q_wt = tf(query_map[term]) * q_idf
            postings_list = self._get_postings(term_offset)
            self._accumulate_scores(scores, postings_list, q_wt)

        # perform length normalization (query and document)
        q_len = math.sqrt(sum(x * x for x in query_map.values()))
        self._normalize(scores, q_len)

        # if havent done relevance feedback, do relevance feedback
        if not self.feedback:
            top_n_docs = self._get_top_n_docs(scores, Engine.NUM_RESULTS)
            stringout = self.relevance_feedback(query_map_copy, top_n_docs)

        # if here, calling from within relevance feedback
        else:
            # return the output of all the scores after relevance feedback
            stringout = " ".join(str(x) for x in scores.keys())

        return stringout
