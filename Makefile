test:
	python kabu_s_test.py \
		--host=${KABU_S_HOST} \
		--port=${KABU_S_PORT} \
		--api_key=${POSTMAN_API_KEY} \
		--postman_return_code=200 \
		--practice \
		--debug
