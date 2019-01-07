# EventMate
A question aggregation engine served over a python flask application.

## Question Aggregation
Similar questions are combined based on the semantic relatedness. [!https://www.aaai.org/Papers/IJCAI/2007/IJCAI07-259.pdf]

The algorithm used is ESA (Explicit Semantic Relatedness), which takes wikipedia documents as corpus. Each question is represented as a weighted vector of Wikipedia-based concepts. Subsequently cosine similarity is computed to access the relatedness.
