test:
	python kabu_s_test.py \
		--data0='japan-stock-prices_2020_9143.csv' \
		--host=${KABU_S_HOST} \
		--port=${KABU_S_PORT} \
		--api_key=${POSTMAN_API_KEY} \
		--postman_return_code=200 \
		--debug

test2:
	python kabu_s_test.py \
		--data0='japan-stock-prices_2021_7974.csv' \
		--host=${KABU_S_HOST} \
		--port=${KABU_S_PORT} \
		--api_key=${POSTMAN_API_KEY} \
		--postman_return_code=200 \
		--debug


conv:
	python add_adj_close.py \
		--input=./japan-stock-prices_2020_9143.csv \
		--output=./japan-stock-prices_2020_%s_adj.csv \
		--dill-input=./rates_df.dill \
		--year=2020 \
		--codes=9143

conv-with-gen:
	python add_adj_close.py \
		--input=./japan-stock-prices_2020_9143.csv \
		--output=./japan-stock-prices_2020_%s_adj.csv \
		--heigou-input=./heigou.html \
		--bunkatsu-input=./bunkatsu.html \
		--dill-output=./rates_df.dill \
		--year=2020 \
		--codes=9143

create-dill:
	python add_adj_close.py \
		--heigou-input=heigou.html \
		--bunkatsu-input=bunkatsu.html \
		--dill-output=rates_df.dill