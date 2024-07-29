kustomizations:
	/bin/bash ./hack/generate_kustomizations.sh

secrets:
	pushd hack && ./generate_secret_templates.sh && popd
