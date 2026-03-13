import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from processing.offer_comparator import print_best_offers

print_best_offers()