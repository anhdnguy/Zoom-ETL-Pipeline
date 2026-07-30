.PHONY: help init plan apply destroy validate fmt clean ssh-key outputs ssm-apiserver redeploy-all dag-upload logs exec db-migrate redeploy status

# Environment variables
ENV ?= prod
TFVARS_FILE = terraform.tfvars
SSO_PROFILE ?= default

help: ## Show this help message
	@echo 'Usage: make [target] ENV=<prod|dev>'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Initialize Terraform
	@echo "Initializing Terraform for $(ENV) environment..."
	cd envs/$(ENV) && terraform init

validate: ## Validate Terraform configuration
	@echo "Validating Terraform configuration..."
	cd envs/$(ENV) && terraform validate

fmt: ## Format Terraform files
	@echo "Formatting Terraform files..."
	terraform fmt -recursive

plan: ## Create Terraform execution plan
	@echo "Creating Terraform plan for $(ENV)..."
	cd envs/$(ENV) && terraform plan -var-file="$(TFVARS_FILE)" -out=tfplan && \
	terraform show -no-color tfplan > tfplan.txt

apply: ## Apply Terraform changes
	@echo "Applying Terraform changes for $(ENV)..."
	cd envs/$(ENV) && terraform apply tfplan
	@echo ""
	@echo "Deployment complete! Run 'make outputs ENV=$(ENV)' to view connection details."

apply-auto: ## Apply without plan (auto-approve)
	@echo "⚠️  Auto-applying Terraform changes for $(ENV)..."
	cd envs/$(ENV) && terraform apply -var-file="$(TFVARS_FILE)" -auto-approve

destroy: ## Destroy infrastructure
	@echo "⚠️  WARNING: This will destroy all infrastructure in $(ENV)!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		cd envs/$(ENV) && terraform destroy -var-file="$(TFVARS_FILE)"; \
	else \
		echo "Destruction cancelled."; \
	fi

import: ## Import current resources
	@read -p "Do you have the resource ADDRESS and ID ready? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		read -p "The terraform resource address (Ex: module.storage.aws_s3_bucket.main): " address; \
		read -p "The resource AWS ID (Ex: smartconnect-dev): " resource_id; \
		cd envs/$(ENV) && terraform import $$address $$resource_id; \
	else \
		echo "Import cancelled."; \
	fi

outputs: ## Show Terraform outputs
	@cd envs/$(ENV) && terraform output

output: ## Show a specific output (usage: make output OUTPUT_NAME=<name>)
	@cd envs/$(ENV) && terraform output -raw $(OUTPUT_NAME)

outputs_summary: ## Show Outputs Summary
	@cd envs/$(ENV) && terraform output summary

state-list: ## List resources in state
	@cd envs/$(ENV) && terraform state list

state-show: ## Show specific resource (usage: make state-show RESOURCE=<name>)
	@cd envs/$(ENV) && terraform state show $(RESOURCE)

cost-estimate: ## Estimate monthly costs (requires infracost)
	@if command -v infracost >/dev/null 2>&1; then \
		cd envs/$(ENV) && infracost breakdown --path .; \
	else \
		echo "infracost not installed. Install from https://www.infracost.io/docs/"; \
	fi

graph: ## Generate dependency graph (requires graphviz)
	@if [ ! -d "envs/$(ENV)/.terraform" ]; then \
		echo "Terraform not initialized. Run 'make init ENV=$(ENV)' first"; \
		exit 1; \
	fi
	@echo "Generating dependency graph for $(ENV)..."
	@cd envs/$(ENV) && terraform graph | dot -Tpng > ../../terraform-graph.png
	@echo "Graph saved to infra/terraform-graph.png"

zip-lambda: ## Zip Zoom Recording Processor
	@cd ../zoom_webhook_catch && \
	find . -type d -name "__pycache__" -exec rm -r {} +; find . -type f -name "*.pyc" -exec rm -f {} + && \
	zip -r zoom_webhook.zip app/

ssm-apiserver: ## SSM tunnel to Airflow UI (http://localhost:8080)
	@cd envs/$(ENV) && eval "$$(terraform output -raw ssm_tunnel_command)"

dag-upload: ## Upload DAG to S3
	@cd envs/$(ENV) && eval "$$(terraform output -raw dag_upload_command)"

redeploy-all: ## Redeploy all Airflow services
	@cd envs/$(ENV) && eval "$$(terraform output -raw redeploy_all_command)"

redeploy: ## Redeploy a single service (usage: make redeploy SERVICE=scheduler)
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make redeploy SERVICE=<webserver|scheduler|triggerer|worker|downloader>"; \
		exit 1; \
	fi
	@CLUSTER=$$(cd envs/$(ENV) && terraform output -raw ecs_cluster_name); \
	SVC_NAME=$$(cd envs/$(ENV) && terraform output -json ecs_services | python3 -c "import sys,json; print(json.load(sys.stdin)['$(SERVICE)'])"); \
	echo "Redeploying $$SVC_NAME..."; \
	aws ecs update-service --cluster $$CLUSTER --service $$SVC_NAME --force-new-deployment --profile $(SSO_PROFILE)

status: ## Show running/desired count for all services
	@CLUSTER=$$(cd envs/$(ENV) && terraform output -raw ecs_cluster_name); \
	SERVICES=$$(cd envs/$(ENV) && terraform output -json ecs_services | python3 -c "import sys,json; print(' '.join(json.load(sys.stdin).values()))"); \
	aws ecs describe-services --cluster $$CLUSTER --services $$SERVICES --profile $(SSO_PROFILE) \
		--query 'services[].{Service:serviceName,Running:runningCount,Desired:desiredCount,Status:status}' --output table