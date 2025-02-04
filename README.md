# deepseek

## Deepseek experiments
* [deepseek-backend](deepseek-backend.py) - FastAPI backend service that wraps various versions of Deepseek including the V3 and R1 models accessible through their API, a asst R1 model hosted by Groq and a local version available via [Ollama](https://ollama.com/).  A version of Perplexity's [sonar-reasoning](https://docs.perplexity.ai/guides/model-cards) reasoning model using R1 is also made available for comparison.  You can run this backend from the command line as follows:
```
$ uvicorn deepseek-backend:app --reload --host 0.0.0.0 --port 8083
```
* [frontend](frontend) - Modern React-based frontend built with [Tailwind CSS](https://tailwindcss.com/), [Next.js](https://nextjs.org/) and [shadcn](https://ui.shadcn.com/) components. Stores history of queries along with metadata about the model used which can be exported. Output is rendered as markdown and can be viewed afterwards form the history pane on the left hand side.  Uses React's `useState` for local state.  Uses IndexedDB for persistent storage.  In order to run this frontend, assuming the backend is up on port 8083, you need to go into the `frontend` directory and invoke:
```
$ npm run dev
```
* [deepseek-frontend](deepseek-frontend.html) - Simple React-based frontend for querying backend built within script tags in html without any support modules.  Stores history of queries along with metadata about the model used which can be exported. Output is rendered as markdown and can be viewed afterwards form the history pane on the left hand side.  Uses React's `useState` for local state.  Uses IndexedDB for persistent storage.  In order to run this frontend assuming the backend is up on port 8083, you just open the [deepseek-frontend](deepseek-frontend.html) file locally in the browser.
* [test-backend](test-backend.py) - Pytest test code for testing the backend.

## Versions of Deepseek
A variety of versions of Deepseek are provided via the New Prompt selector:
<img width="1039" alt="image" src="https://github.com/user-attachments/assets/2665de4e-d55d-4ee8-bf07-4066bd76b8be" />
The options are as follows:
* **Deepseek V3** - this is the version Deepseek's V3 chat model provided by HighFlyer through their API documented [here](https://api-docs.deepseek.com/).
* **Deepseek R1** - this is the version Deepseek's R1 reasoning model provided by HighFlyer through their API documented [here](https://api-docs.deepseek.com/).
* **Groq Deepseek** - this is a version of Deepseek's R1 reasoning model provided by Groq hosted in their US data centre on specialised hardware.  It's super fast!  See [here](https://console.groq.com/docs/models) for details.
* **Perplexity Sonar Deepseek** - this is a version of Deepseek's R1 reasoning model provided by Perplexity in the form of their `solar-reasoning` model documented [here](https://docs.perplexity.ai/guides/model-cards).
* **Ollama Deepseek** - this is Deepseek's R1 reasoning model made available via Ollama meaning it is locally hosted.  Ollama is built into its own Docker container.  See [here](https://ollama.com/library/deepseek-r1) for more details.
* **Gumtree Deepseek** - tbd

##  frontend
### Prompt pane view
<img width="1145" alt="image" src="https://github.com/user-attachments/assets/509fc8ba-8091-4fa8-b88a-7742f93be156" />

### History pane view
<img width="1145" alt="image" src="https://github.com/user-attachments/assets/dba531cd-2bc9-44a7-82c8-8f2717c7e398" />

##  deepseek-frontend
### Prompt pane view
<img width="1507" alt="image" src="https://github.com/user-attachments/assets/6a8cd6a5-b9c8-4263-b317-45af2d2c587c" />

### History pane view
<img width="1507" alt="image" src="https://github.com/user-attachments/assets/9e85921a-b11c-49d6-9973-53b401647001" />

##  Dockerisation
You will need to have docker and terraform setup locally.  You will then need to create a local `terraform.tfvars` file containing the following secrets: 
```
deepseek_api_key = "<deepseek api key here>"
groq_api_key = "<groq api key here>"
perplexity_api_key = "<perplexity pro api key here>"
```
Then run the following command to build the containers:
```
$ docker compose down 2>/dev/null; docker rm -f $(docker ps -a -q --filter name=deepseek*) 2>/dev/null; docker rmi -f deepseek-frontend:latest deepseek-backend:latest 2>/dev/null; docker network rm deepseek-network 2>/dev/null; rm -rf .terraform terraform.tfstate* 2>/dev/null; terraform init && terraform apply --auto-approve
```
It may take a while to run the first time as it is building out the ollama container.  If all has run according to plan then you should see three new containers visible:
```
deepseek % docker ps | grep "deepseek\|ollama"
4523339beeb7   deepseek-frontend:latest   "/docker-entrypoint.…"   31 minutes ago   Up 17 minutes             80/tcp, 0.0.0.0:8082->8082/tcp   deepseek-frontend
9f638a3a3dfb   deepseek-backend:latest    "uvicorn deepseek-ba…"   31 minutes ago   Up 17 minutes             0.0.0.0:8083->8083/tcp           deepseek-backend
2b52d203d974   ollama/ollama:0.5.6        "/bin/sh -c 'ollama …"   31 minutes ago   Up 17 minutes (healthy)   0.0.0.0:11434->11434/tcp         ollama
```
You should also be able to see them in Docker Desktop:
<img width="1501" alt="image" src="https://github.com/user-attachments/assets/f22e8f93-1986-4cf5-b4ea-883ab6ece274" />
Note that the Docker container for the frontend currently builds out [deepseek-frontend](deepseek-frontend.html),

##  Documentation
Backend Swagger API documentation is visible at http://localhost:8083/docs
<img width="1501" alt="image" src="https://github.com/user-attachments/assets/e3da22ad-ddfe-454e-8b75-dbd6d930b450" />
