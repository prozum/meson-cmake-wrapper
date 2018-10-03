import sys
from .cmake import CMakeWrapper


def main():
    CMakeWrapper().run(sys.argv)


if __name__ == "__main__":
    main()
