# deepseek

## Deepseek experiments
* [deepseek-backend](deepseek-backend.py) - FastAPI backend service that wraps various versions of Deepseek including the V3 and R1 models accessible through their API, a asst R1 model hosted by Groq and a local version available via [Ollama](https://ollama.com/).  A version of Perplexity's [sonar]() reasoning model is also made available for comparison. 
* [deepseek-frontend](deepseek-frontend.html) - React-based frontend for querying backend.  Now improved to store history along with metadata about the model used.  This can be exported. Output is rendered as markdown and can be viewed afterwards form the history pane on the left hand side.
* [test-backend](test-backend.py) - Pytest test code for testing the backend.

##  Screenshots
### Prompt pane view
<img width="1507" alt="image" src="https://github.com/user-attachments/assets/6a8cd6a5-b9c8-4263-b317-45af2d2c587c" />

### History pane view
<img width="1507" alt="image" src="https://github.com/user-attachments/assets/9e85921a-b11c-49d6-9973-53b401647001" />

##  Dockerisation
You will need to have docker and terraform setup locally.  You will then need to create a local terraform.tfvars file containing the following secrets: 
```
deepseek_api_key = "<deepseek api key here>"
groq_api_key = "<groq api key here>"
perplexity_api_key = "<perplexity pro api key here>"
```
Then run the following command to build the containers:
```
$ docker stop deepseek-frontend deepseek-backend; docker rm deepseek-frontend deepseek-backend; docker rmi deepseek-frontend:latest deepseek-backend:latest; docker network rm deepseek-network; rm -rf .terraform terraform.tfstate* && terraform init && terraform apply --auto-approve
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

##  Documentation
Backend documentation is visible at http://localhost:8083/docs
<img width="1501" alt="image" src="https://github.com/user-attachments/assets/e3da22ad-ddfe-454e-8b75-dbd6d930b450" />
