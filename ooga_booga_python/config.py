target_token = "0xFCBD14DC51f0A4d49d5E53C2E0950e0bC26d0Dce" # HONEY

excluded_tokens = [
    "bera",  # BERA
    "0x656b95E550C07a9ffe548bd4085c72418Ceb1dba", # BGT
    #"0x6969696969696969696969696969696969696969", # WBERA
    target_token  # 保留目标token
]

max_retries = 5
request_delay = 5
slippage = 0.02