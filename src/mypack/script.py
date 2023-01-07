"""
I am trying out packges in Python. I want to include a function into another file.

Module = file?
package = dir?

"""
import sys
from mypack import pack

# import pack
# from pack import pack

if __name__ == "__main__":
    # sys.path.append(".")
    print(sys.path)
    pack.this_func()  # doesn't work
