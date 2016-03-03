import argparse
from shunting_yard import get_reverse_polish
from search_engine import execute_query

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--dictionary', required=True,
                    help='dictionary file')
parser.add_argument('-p', '--postings', required=True,
                    help='postings file')
parser.add_argument('-q', '--queries', required=True,
                    help='file of queries')
parser.add_argument('-o', '--output', required=True,
                    help='file of results')
parser.add_argument('--debug', dest='debug', default=False,
                    action='store_true', help='debug mode')
args = parser.parse_args()

with open(args.queries, 'r') as fq, open(args.output, 'w') as fo:
    for query in fq:
        reverse_polish = get_reverse_polish(query)
        fo.write(str(execute_query(reverse_polish)) + '\n')
