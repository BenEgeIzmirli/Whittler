import os
import sys
WHITTLER_DIRNAME = os.path.dirname(os.path.realpath(__file__))
sys.path.append(WHITTLER_DIRNAME)
from Whittler import main

main()