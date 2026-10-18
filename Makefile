REGION           ?= eu-west-1
CLUSTER          ?= portfolio
ARGOCD_CHART_VER ?= 10.10.5   # chart ships Argo CD v3.x — bump deliberately
TFVARS           := terraform/cluster/cluster.tfvars

.PHONY: help kind-up kind-down install-kind local-up local-down up down fwd-argocd fwd-grafana

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

kind-up: ## kind cluster + patched metrics-server (HPA demos work locally)
	kind create cluster --name $(CLUSTER)
	kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
	kubectl -n kube-system patch deployment metrics-server --type=json \
	  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
	kubectl -n kube-system rollout status deployment/metrics-server --timeout=120s

kind-down: ## delete the kind cluster
	kind delete cluster --name $(CLUSTER)

install-kind: ## helm-install the 3 services from the local chart (phase-3 practice)
	for svc in frontend products orders; do \
	  helm upgrade --install $$svc charts/microservice -f gitops/apps/$$svc/values.yaml -n $$svc --create-namespace; \
	done

local-up: ## run the app with docker compose, no cluster involved
	docker compose up --build

local-down: ## stop the compose stack
	docker compose down

up: ## full EKS session: terraform -> kubeconfig -> argocd -> root app
	@test -f $(TFVARS) || { echo "copy $(TFVARS).example to $(TFVARS) and set your IP"; exit 1; }
	cd terraform/cluster && terraform apply -auto-approve -var-file=cluster.tfvars
	aws eks update-kubeconfig --name $(CLUSTER) --region $(REGION)
	helm repo add argo https://argoproj.github.io/argo-helm || true
	helm repo update
	helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace --version $(ARGOCD_CHART_VER)
	kubectl apply -f gitops/bootstrap/root-app.yaml
	@echo "-- ArgoCD admin password:"
	@kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo

down: ## teardown: apps first (releases the LB), wait for AWS, then destroy
	-kubectl delete application root -n argocd --wait
	@echo "-- waiting for load balancers to disappear (classic AND v2)..."
	@until [ -z "$$(aws elbv2 describe-load-balancers --region $(REGION) --query 'LoadBalancers[].LoadBalancerArn' --output text 2>/dev/null)" ] \
	   && [ -z "$$(aws elb describe-load-balancers --region $(REGION) --query 'LoadBalancerDescriptions[].LoadBalancerName' --output text 2>/dev/null)" ]; do \
	  sleep 15; \
	done
	-helm uninstall argocd -n argocd
	@test -f $(TFVARS) || { echo "copy $(TFVARS).example to $(TFVARS)"; exit 1; }
	cd terraform/cluster && terraform destroy -auto-approve -var-file=cluster.tfvars

fwd-argocd: ## ArgoCD UI on localhost:8080
	kubectl port-forward svc/argocd-server -n argocd 8080:443

fwd-grafana: ## Grafana UI on localhost:3000
	kubectl port-forward svc/monitoring-grafana -n monitoring 3000:80
