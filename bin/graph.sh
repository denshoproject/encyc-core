sfood --internal --ignore-unused . | grep -v tests | sfood-graph | dot -Tsvg > encyc-core-graph.svg
