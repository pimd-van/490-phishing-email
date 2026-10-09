# XAI phishing project

This glossary distinguishes email predictions from the reference material used to explain them.

## Language

**Handoff email**:
An email from the MeAJOR test split that Part 1 predicted as phishing. It is input to Part 2, not a knowledge-base document.

**Guidance document**:
A trusted phishing-prevention or response text supplied as a UTF-8 `.txt` or `.md` file. It is the source material indexed for retrieval.

**Chunk**:
A bounded passage from one guidance document with a stable source reference. It is the unit returned by retrieval.

**Knowledge-base index**:
The local Chroma collection of guidance-document chunks. It does not contain handoff emails or ground-truth labels.
