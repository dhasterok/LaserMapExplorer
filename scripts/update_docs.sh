#!/bin/bash

cd ../lame-core && python -m sphinx -b html docs/source docs/build/html
cd ../siesta-rest-editor && python -m sphinx -b html docs/source docs/build/html
cd ../blueberry-colortools && python -m sphinx -b html docs/source docs/build/html
cd ../global_geochemistry && python -m sphinx -b html docs/source docs/build/html
cd ..LaserMapExplorer && python -m sphinx -b html docs/source docs/build/html