import sys

r = int(sys.argv[1])
g = int(sys.argv[2])
b = int(sys.argv[3])

print("#{:02x}{:02x}{:02x}".format(r, g, b))
