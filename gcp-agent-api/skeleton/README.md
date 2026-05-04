  _IMAGE_URI: ''
  _IMAGE_VERSION: ''
  _SERVICE_NAME: ''
  _CLOUDRUN_SERVICE_ACCOUNT: ''
  _PORT: ''
  _MIN_INSTANCES: ''
  _MAX_INSTANCES: ''
  _CPU: ''
  _MEMORY: ''
  _BUILD_SERVICE_ACCOUNT: ''
  _REGION: ''
  # _INGRESS: 'internal' # internal doesnt work with APIGateay https://issuetracker.google.com/issues/237250997
  _INGRESS: ''
  _VPC_EGRESS: ''
  _NETWORK: ''
  _SUBNET: '' # Specify your subnet name if needed
  _WORKER_POOL_NAME: ''
  _ARIZE_API_KEY_NAME: ''
  _ARIZE_SPACE_ID_NAME: ''

gcloud builds triggers delete gcp-agentapi-trigger-dev  --region="us-east4"
gcloud builds triggers delete gcp-agentapi-trigger-demo  --region="us-central1"
gcloud builds triggers delete gcp-agentapi-trigger-stage1  --region="europe-west4"

gcloud builds triggers create github --name="gcp-agentapi-trigger-demo"  --region="us-central1"    --branch-pattern="^develop$" --build-config="gcp/gcp-agent-api/skeleton/cloudbuild.yaml" --repository="projects/<PROJECT_ID>/locations/us-central1/connections/github-neuroaiengineering-demo/repositories/Cognizant-AIForEnterprise-scaffolder-templates" --included-files="gcp/gcp-agent-api/**" --service-account="projects/<PROJECT_ID>/serviceAccounts/neuroaieng-cloudbuild-sa@<PROJECT_ID>.iam.gserviceaccount.com" --substitutions=_IMAGE_URI='us-east4-docker.pkg.dev/<PROJECT_ID>/neuroaiengineering-repo/demo/neuroaiengineering-agent-api',_IMAGE_VERSION='v1',_SERVICE_NAME='neuroaiengineering-agent-api',_CLOUDRUN_SERVICE_ACCOUNT='neuroaieng-cloudrun-sa@<PROJECT_ID>.iam.gserviceaccount.com',_PORT='8080',_MIN_INSTANCES='1',_MAX_INSTANCES='2',_CPU='1',_MEMORY='1Gi',_BUILD_SERVICE_ACCOUNT='projects/<PROJECT_ID>/serviceAccounts/neuroaieng-cloudbuild-sa@<PROJECT_ID>.iam.gserviceaccount.com',_REGION='us-central1',_INGRESS='internal',_VPC_EGRESS='all-traffic',_NETWORK='vpc-neuroaiengineering-demo',_SUBNET='neuroaiengineering-cloudrun-subnet',_WORKER_POOL_NAME='',_ARIZE_API_KEY_NAME='ARIZE_API_KEY',_ARIZE_SPACE_ID_NAME='ARIZE_SPACE_ID'

gcloud builds triggers create github --name="gcp-agentapi-trigger-dev"  --region="us-east4"    --branch-pattern="^develop$" --build-config="gcp/gcp-agent-api/skeleton/cloudbuild.yaml" --repository="projects/<PROJECT_ID>/locations/us-east4/connections/github-neuroaiengineering-dev/repositories/Cognizant-AIForEnterprise-scaffolder-templates" --included-files="gcp/gcp-agent-api/**" --service-account="projects/<PROJECT_ID>/serviceAccounts/neuroaieng-cloudbuild-sa@<PROJECT_ID>.iam.gserviceaccount.com" --substitutions=_IMAGE_URI='us-east4-docker.pkg.dev/<PROJECT_ID>/neuroaiengineering-repo/dev/neuroaiengineering-agent-api',_IMAGE_VERSION='v1',_SERVICE_NAME='neuroaiengineering-agent-api',_CLOUDRUN_SERVICE_ACCOUNT='neuroaieng-cloudrun-sa@<PROJECT_ID>.iam.gserviceaccount.com',_PORT='8080',_MIN_INSTANCES='1',_MAX_INSTANCES='2',_CPU='1',_MEMORY='1Gi',_BUILD_SERVICE_ACCOUNT='projects/<PROJECT_ID>/serviceAccounts/neuroaieng-cloudbuild-sa@<PROJECT_ID>.iam.gserviceaccount.com',_REGION='us-east4',_INGRESS='internal',_VPC_EGRESS='all-traffic',_NETWORK='vpc-neuroaiengineering-dev',_SUBNET='neuroaiengineering-cloudrun-subnet',_WORKER_POOL_NAME='',_ARIZE_API_KEY_NAME='ARIZE_API_KEY',_ARIZE_SPACE_ID_NAME='ARIZE_SPACE_ID'


gcloud builds triggers create github --name="gcp-agentapi-trigger-stage1"  --region="europe-west4"    --branch-pattern="^main$" --build-config="gcp/gcp-agent-api/skeleton/cloudbuild.yaml" --repository="projects/<PROJECT_ID>/locations/europe-west4/connections/github-neuroaiengineering-stage1/repositories/Cognizant-AIForEnterprise-scaffolder-templates" --included-files="gcp/gcp-agent-api/**" --service-account="projects/<PROJECT_ID>/serviceAccounts/neuroaieng-cloudbuild-sa@<PROJECT_ID>.iam.gserviceaccount.com" --substitutions=_IMAGE_URI='us-east4-docker.pkg.dev/<PROJECT_ID>/neuroaiengineering-repo/stage1/neuroaiengineering-agent-api',_IMAGE_VERSION='v1',_SERVICE_NAME='neuroaiengineering-agent-api',_CLOUDRUN_SERVICE_ACCOUNT='neuroaieng-cloudrun-sa@<PROJECT_ID>.iam.gserviceaccount.com',_PORT='8080',_MIN_INSTANCES='1',_MAX_INSTANCES='2',_CPU='1',_MEMORY='1Gi',_BUILD_SERVICE_ACCOUNT='projects/<PROJECT_ID>/serviceAccounts/neuroaieng-cloudbuild-sa@<PROJECT_ID>.iam.gserviceaccount.com',_REGION='europe-west4',_INGRESS='internal',_VPC_EGRESS='all-traffic',_NETWORK='vpc-neuroaiengineering-stage1',_SUBNET='neuroaiengineering-cloudrun-subnet',_WORKER_POOL_NAME='',_ARIZE_API_KEY_NAME='ARIZE_API_KEY',_ARIZE_SPACE_ID_NAME='ARIZE_SPACE_ID'
