#!/bin/bash
pp thinking_a8.map |
/usr/bin/pandoc -f markdown -t html5 \
   -o /tmp/think.html \
   --self-contained \
   --metadata title="Кейс A8" \
   --toc \
   -
# cleanup: remove temporary files
ls -1 | ag 'graphviz-[0-9a-f]{64}.png' | xargs rm

#   -F ~/bin/pandoc-filter-graphviz \
