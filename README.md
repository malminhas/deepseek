# deepseek

## Deepseek experiments
* [search-backend](search-backend.py) - FastAPI backend service that wraps various versions of Deepseek including the V3 and R1 models accessible through their API, a asst R1 model hosted by Groq and a local version available via [Ollama](https://ollama.com/).  A version of Perplexity's [sonar]() reasoning model is also made available. 
* [search-frontend](search-frontend.html) - React-based frontend for querying backend.  Now improved to store history along with metadata about the model used.  This can be exported. Output is rendered as markdown.
* [test-backend](test-backend.py) - Pytest test code for testing the backend.

##  Screenshots
### Prompt pane view
<img width="1507" alt="image" src="https://github.com/user-attachments/assets/6a8cd6a5-b9c8-4263-b317-45af2d2c587c" />

### History pane view
<img width="1507" alt="image" src="https://github.com/user-attachments/assets/9e85921a-b11c-49d6-9973-53b401647001" />
