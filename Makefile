SHELL = /usr/bin/env bash -xeuo pipefail

stack_name:=PyconServerlessTutorial

lint:
	@for handler in $$(find src -maxdepth 1 -type d); do \
		dir_name=$$(basename $$handler); \
		if [[ $$dir_name =~ src ]]; then continue; fi; \
		pipenv run flake8 $$handler; \
		pipenv run mypy --ignore-missing-imports $$handler; \
	done

	pipenv run flake8 tests

build: clean
	@for src_dir in $$(find src -type d -maxdepth 1); do \
		dir_name=$$(basename $$src_dir); \
		if [[ $$dir_name =~ src ]]; then continue; fi; \
		root_dir=$$PWD; \
		[[ ! -f $$src_dir/Pipfile ]] && touch $$src_dir/requirements.txt || echo ''; \
		[[ -f $$src_dir/Pipfile ]] && cd $$src_dir && pipenv lock --requirements > requirements.txt && cd $$root_dir || echo ''; \
	done
	pipenv run sam build -u -t sam.yml

package: build
	pipenv run sam package --s3-bucket $$SAM_ARTIFACT_BUCKET --output-template-file template.yml

deploy: package
	pipenv run sam deploy \
		--template-file template.yml \
		--stack-name $(stack_name) \
		--capabilities CAPABILITY_IAM \
		--no-fail-on-empty-changeset
	pipenv run aws cloudformation describe-stacks \
		--stack-name $(stack_name) \
		--query Stacks[0].Outputs

destroy:
	STACK_NAME=$(stack_name) pipenv run python make_bucket_empty.py
	pipenv run aws cloudformation delete-stack --stack-name $(stack_name)
	pipenv run aws cloudformation wait stack-delete-complete --stack-name $(stack_name)

echo:
	echo $(stack_name)

clean:
	@find src/** -type d \( -name '__pycache__' -o -name '*\.dist-info' -o -name '*\.egg-info' \) -print0 | xargs -0 -n1 rm -rf
	@find src/** -type f \( -name '.coverage' -o -name '*.pyc' \) -print0 | xargs -0 -n1 rm -rf
	@find src/** -type f -name requirements.txt | xargs rm -f

localstack-up:
	docker-compose up -d

localstack-stop:
	docker-compose stop

localstack-down:
	docker-compose down

test-unit: localstack-up
	@for handler in $$(find src -maxdepth 1 -type d); do \
		dir_name=$$(basename $$handler); \
		if [[ $$dir_name =~ src ]]; then continue; fi; \
		AWS_DEFAULT_REGION=ap-northeast-1 \
		AWS_ACCESS_KEY_ID=dummy \
		AWS_SECRET_ACCESS_KEY=dummy \
		PYTHONPATH=$$handler \
			python -m pytest -v tests/unit/$$dir_name; \
	done

.PHONY: \
	build \
	package \
	deploy \
	echo \
	clean \
	destroy \
	localstack-up \
	localstack-stop \
	localstack-down
