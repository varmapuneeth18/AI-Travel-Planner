# Deployment

Deployment assets are included under [deployment/Dockerfile](/Users/sumanthvarma/Downloads/Travel-Book-master/deployment/Dockerfile), [deployment/cloudbuild.yaml](/Users/sumanthvarma/Downloads/Travel-Book-master/deployment/cloudbuild.yaml), and [deployment/terraform/main.tf](/Users/sumanthvarma/Downloads/Travel-Book-master/deployment/terraform/main.tf).

Target architecture:

- Cloud Run for the FastAPI service
- Vertex AI for model inference
- Cloud Storage for logs and reports
- Firestore for session persistence

Recommended rollout:

1. Build and push the image with Cloud Build.
2. Apply Terraform for storage, Firestore, and Cloud Run.
3. Inject environment variables for models, embeddings, and storage paths.
4. Route dashboard and batch experiments separately if needed.
