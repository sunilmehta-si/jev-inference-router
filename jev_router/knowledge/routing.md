# Routing policy and uncertainty

The application checks a small allowlist of configuration questions in Python first.
For other questions, Jev selects local_llm, retrieve, or clarify using Choice. Noul
estimates whether more context is required. Score evaluates candidate documentation
against three relevance levels: irrelevant, related but insufficient, directly useful.

Default route confidence threshold is 0.65. This is a demonstration starting point,
not a calibrated production threshold. Low confidence or a needs-context probability
of at least 0.65 leads to clarification. Retrieval keeps documents with relevance
score at least 1.2. No suitable document leads to clarification. TypeSafe outages
also lead to clarification; they are never reported as successful Jev decisions.
The router does not execute shell commands or change infrastructure.
