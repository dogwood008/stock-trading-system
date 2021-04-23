test:
	python kabu_s_test.py \
		--data0='japan-stock-prices_2021_7974.csv' \
		--host=${KABU_S_HOST} \
		--port=${KABU_S_PORT} \
		--api_key=${POSTMAN_API_KEY} \
		--postman_return_code=200 \
		--debug
