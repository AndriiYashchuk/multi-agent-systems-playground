## Report

# What is RAG (Retrieval-Augmented Generation)?

**Retrieval-Augmented Generation (RAG)** is a way of improving an AI model’s answers by letting it **look up relevant information first** and then **use that information to generate a response**.

In simple terms, a normal language model answers mostly from what it learned during training. A RAG system adds a search step, so the model can use external sources such as documents, web pages, manuals, or internal company knowledge.

## Core idea

RAG combines three main parts:

- **Retriever**: finds relevant information for the user’s question
- **Knowledge source**: the documents or database being searched
- **Generator**: the language model that writes the final answer

## How RAG works

A basic RAG flow looks like this:

1. A user asks a question.
2. The system searches a knowledge source for relevant content.
3. It selects the most useful passages.
4. Those passages are given to the language model as context.
5. The model generates an answer grounded in that retrieved information.

A good mental model is: **RAG is like an open-book exam**, while a standard LLM is more like answering from memory.

## Why it’s useful

RAG is popular because language models by themselves can have limitations:

- their knowledge may be **out of date**
- they may not know **private or company-specific information**
- they can sometimes **hallucinate** or confidently say incorrect things

RAG helps by giving the model fresh, relevant information at answer time. That often leads to:

- more accurate factual answers
- access to internal or specialized knowledge
- easier updates without retraining the model
- better transparency when answers include sources or citations

## Limitations

RAG is useful, but it is not magic.

- If retrieval finds the wrong documents, the answer can still be wrong.
- The model can still misunderstand or overstate the retrieved content.
- It adds extra system complexity and can slow responses slightly.
- Results depend heavily on the quality of the underlying documents.

## RAG vs a standard LLM

- **Standard LLM**: answers from training knowledge alone
- **RAG system**: answers using both the model’s trained ability and retrieved external information

So, RAG is especially helpful when answers need to be tied to specific documents, up-to-date information, or private knowledge.

## RAG vs fine-tuning

These solve different problems:

- **RAG** adds knowledge at runtime
- **Fine-tuning** changes the model’s behavior through additional training

A simple rule of thumb:

- use **RAG** when the model needs **better or fresher information**
- use **fine-tuning** when the model needs **different behavior, style, or task skill**

## Short summary

RAG is a method where an AI system **retrieves relevant information first and generates an answer second**. It makes AI responses more grounded, more current, and more useful for document-based or knowledge-heavy tasks.

## Sources

- AWS: https://aws.amazon.com/what-is/retrieval-augmented-generation/
- IBM: https://www.ibm.com/think/topics/retrieval-augmented-generation
- Microsoft Learn: https://learn.microsoft.com/en-us/azure/developer/ai/augment-llm-rag-fine-tuning