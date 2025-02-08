# main.tf
# -------
# This code automates building, networking, and deploying Dockerized backend and frontend
# applications in a controlled environment. It uses Terraform to define and manage the
# infrastructure, Docker to containerize the frontend and backend, and Docker Compose to
# orchestrate the two containers.  The code ensures that the backend and frontend are built,
# networked, and deployed in a controlled manner, with the frontend depending on the backend.
# -------
# Define the Terraform block with required provider information

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.0"
    }
  }
}

# Configures the Docker provider to interact with Docker via the Unix socket.
provider "docker" {
  host = "unix:///var/run/docker.sock"
}

# Local build of deepseek backend image
resource "null_resource" "deepseek_backend_build" {
  provisioner "local-exec" {
    command = "docker build -t deepseek-backend:latest -f ../docker/Dockerfile.backend .."
  }

  # Force the build to run every time by using a trigger based on the current timestamp
  triggers = {
    always_run = "${timestamp()}"
  }
}

# Local build of deepseek frontend image
resource "null_resource" "deepseek_frontend_build" {
  provisioner "local-exec" {
    command = "docker build -t deepseek-frontend:latest -f ../docker/Dockerfile.frontend .."
  }

  # Force the build to run every time by using a trigger based on the current timestamp
  triggers = {
    always_run = "${timestamp()}"
  }
}

# Local build of new frontend image
resource "null_resource" "deepseek_frontend_new_build" {
  provisioner "local-exec" {
    command = "docker build -t deepseek-frontend-new:latest -f ../docker/Dockerfile.frontend-new .."
  }

  triggers = {
    always_run = "${timestamp()}"
  }
}

# Define a Docker image resource for the backend.
# Specify the name of the Docker image. Keep the image locally after it's pulled.
# Depend on the backend build to ensure the image is built before the container is created.
resource "docker_image" "deepseek_backend" {
  name = "deepseek-backend:latest"
  keep_locally = true
  depends_on = [null_resource.deepseek_backend_build]
}

# Define a Docker image resource for the original frontend
# Specify the name of the Docker image. Keep the image locally after it's pulled.
# Depend on the frontend build to ensure the image is built before the container is created.
resource "docker_image" "deepseek_frontend" {
  name = "deepseek-frontend:latest"
  keep_locally = true
  depends_on = [null_resource.deepseek_frontend_build]
}

# Define Docker image resource for the new frontend 
# built using tailwind, nextjs, and shadcn/ui and shadcn/ui-react
resource "docker_image" "deepseek_frontend_new" {
  name = "deepseek-frontend-new:latest"
  keep_locally = true
  depends_on = [null_resource.deepseek_frontend_new_build]
}

# Update the Ollama image to use a specific version
resource "docker_image" "ollama" {
  name = "ollama/ollama:0.5.6"  # Using a specific, stable version
}

# Enhanced cleanup resource for both network and containers
resource "null_resource" "cleanup" {
  provisioner "local-exec" {
    command = <<-EOT
      # Stop and remove the ollama container if it exists
      docker stop ollama 2>/dev/null || true
      docker rm ollama 2>/dev/null || true
      
      # Stop and remove all project containers
      docker ps -a | grep 'deepseek-' | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
      
      # Get all containers connected to the network
      CONTAINERS=$(docker network inspect deepseek-network -f '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "")
      
      # Disconnect each container from the network
      for container in $CONTAINERS; do
        docker network disconnect -f deepseek-network $container 2>/dev/null || true
      done
      
      # Remove the network
      docker network rm deepseek-network 2>/dev/null || true
      
      # Wait a moment to ensure cleanup is complete
      sleep 2
    EOT
    interpreter = ["/bin/bash", "-c"]
  }
}

# Update network resource to depend on cleanup
resource "docker_network" "deepseek_network" {
  name = "deepseek-network"
  driver = "bridge"
  depends_on = [null_resource.cleanup]
}

# Define a Docker container for the backend.
# Specify the container name and image.
# Network the container to the app network.
# Map the internal port 8081 to the external port 8081.
resource "docker_container" "deepseek_backend" {
  name  = "deepseek-backend"
  image = docker_image.deepseek_backend.name

  # Set the container's hostname to the container's name.
  networks_advanced {
    name = docker_network.deepseek_network.name
  }

  # Map the internal port 8083 to the external port 8083.
  ports {
    internal = 8083
    external = var.deepseek_backend_port
  }

  env = [
    "DEEPSEEK_API_KEY=${var.deepseek_api_key}",
    "GROQ_API_KEY=${var.groq_api_key}",
    "PERPLEXITY_API_KEY=${var.perplexity_api_key}",
    "GUMTREE_API_URL=${var.gumtree_api_url}",
    "CORS_ORIGINS=http://localhost",
    "OLLAMA_HOST=http://ollama:11434"
  ]

  # Configure the container to restart unless stopped manually
  restart = "unless-stopped"

  depends_on = [
    docker_container.ollama
  ]
}

# Define a Docker container for the frontend.
# Specify the container name and image.
# Network the container to the app network.
# Map the internal port 80 to the external port 80.
resource "docker_container" "reviews_frontend" {
  name  = "deepseek-frontend"
  image = docker_image.deepseek_frontend.name

  # Set the container's hostname to the container's name.
  networks_advanced {
    name = docker_network.deepseek_network.name
  }

  # Map the internal port 8082 to the external port 8082.
  ports {
    internal = 8082
    external = var.deepseek_frontend_port
  }

  # Depend on the backend container to ensure it's running before the frontend container is created.
  depends_on = [
    docker_container.deepseek_backend
  ]
}

# Container for the new frontend built using 
# tailwind, nextjs, and shadcn/ui and shadcn/ui-react
resource "docker_container" "deepseek_frontend_new" {
  name  = "deepseek-frontend-new"
  image = docker_image.deepseek_frontend_new.name

  networks_advanced {
    name = docker_network.deepseek_network.name
  }

  ports {
    internal = 8084
    external = 8084
  }

  depends_on = [
    docker_container.deepseek_backend
  ]
}

# Add Ollama container with model initialization
resource "docker_container" "ollama" {
  name  = "ollama"
  image = docker_image.ollama.name
  
  networks_advanced {
    name = docker_network.deepseek_network.name
  }

  # Expose Ollama API port
  ports {
    internal = 11434
    external = 11434
  }

  # More robust startup script
  entrypoint = ["/bin/sh", "-c"]
  command = [
    <<-EOT
    ollama serve & 
    echo "Waiting for Ollama server to start..."
    sleep 15

    # Function to check if model exists
    check_model() {
      ollama list 2>/dev/null | grep -q "deepseek-r1"
    }

    # Try to pull the model with retries
    max_attempts=3
    attempt=1
    while [ $attempt -le $max_attempts ]; do
      echo "Attempt $attempt to pull deepseek-r1 model..."
      
      if ollama pull deepseek-r1:latest; then
        echo "Model pulled successfully"
        if check_model; then
          echo "Model verified and ready!"
          break
        fi
      fi
      
      echo "Pull attempt $attempt failed, waiting before retry..."
      sleep 30
      attempt=$((attempt + 1))
    done

    if ! check_model; then
      echo "Failed to pull model after $max_attempts attempts"
      exit 1
    fi

    tail -f /dev/null
    EOT
  ]

  restart = "unless-stopped"

  # Add healthcheck
  healthcheck {
    test = ["CMD-SHELL", "ollama list 2>/dev/null | grep -q 'deepseek-r1' || exit 1"]
    interval = "30s"
    timeout  = "10s"
    retries  = 3
    start_period = "180s"  # Longer start period to account for model download
  }
}
