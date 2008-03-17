#!/bin/bash
echo "testing grammars"
../grapher.py -o grammar1.png -i '-+i-i*(i+i)/i+i' grammar.pyl grammar.pyg
../grapher.py -o grammar2.png -i 'a*a-a*!a+a/(a;)<a' grammar2.pyl grammar2.pyg
../grapher.py -o grammar3.png -i 'begin id := (id+id); end' grammar3.pyl grammar3.pyg
echo "test complete"
