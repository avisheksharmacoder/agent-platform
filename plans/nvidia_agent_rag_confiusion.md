# The NVIDIA Agent RAG Confusion Bug

## What is the Problem?
When you use a powerful language model like NVIDIA's Nemotron to generate responses in a rigid format (like JSON), the backend system uses a "grammar parser" to force the model to output exactly what you asked for.

However, when our AI Chat system uses the **RAG (Retrieval-Augmented Generation)** feature to fetch older tickets from the database, it grabs the raw contents of those old tickets. If an old ticket happens to contain code with curly braces `{ }` (like SAPUI5 manifest code), this gets injected directly into the prompt history.

When the LLM reads this prompt containing `{ }` and tries to write its own structured JSON response, its grammar parser gets confused by the overlapping curly braces. It misinterprets the `{` inside the old ticket as part of its *own* required output structure, panics, and forcefully closes the JSON object early to prevent an error. 

This results in the AI returning a broken response (like `}}`), which shows up as an empty chat bubble in the Vue UI.

## A Simple Example

Imagine you ask the LLM to output a JSON object like this:
```json
{
  "action": "respond",
  "content": "<ANSWER HERE>"
}
```

Now, the RAG tool fetches an old ticket about SAPUI5 and injects this into the prompt:
*"User needs help with this code: { "sap.app": { "id": "my.app" } }"*

The LLM starts generating its answer:
```json
{
  "action": "respond",
  "content": "Here is your code: { "sap.app": 
```
At this exact moment, the NVIDIA JSON grammar engine sees the `{` and `}` and gets violently confused. It tries to "fix" the JSON by abruptly stopping the text and closing out the outer brackets, resulting in the system just receiving `}}` as the final content.

## The Solution
Instead of having the `search_knowledge_base` tool return a raw JSON dictionary (which Pydantic-AI feeds directly to the model), we will make the tool return a **plain, human-readable text string**. 

To ensure the Vue frontend still gets the structured data (the clickable "AI retrieved 1 document(s)" accordion), we will secretly stash the structured data in a `ChatDependencies` object before returning the plain text to the LLM. 

This gives the LLM clean, readable text to process without triggering the grammar bug, while preserving the complex data for the UI!
