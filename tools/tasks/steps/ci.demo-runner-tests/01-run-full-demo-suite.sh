cd scripts
python demo_suite_runner.py --seed "${{ env.STEGVERSE_SEED }}" --tests 5 --mode deterministic --output ../demo_result.json
