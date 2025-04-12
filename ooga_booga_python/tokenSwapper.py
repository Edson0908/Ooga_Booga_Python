import asyncio
import os
from dotenv import load_dotenv
from typing import List, Set
import aiohttp
from client import OogaBoogaClient
from models import SwapParams, Token
from web3 import Web3
from eth_account import Account
import config
import json
import custom_logger

logger = custom_logger.get_logger(__name__)

class TokenSwapper:
    def __init__(self, client: OogaBoogaClient, debank_api_key: str):
        self.client = client
        self.debank_api_key = debank_api_key
        self.debank_base_url = "https://pro-openapi.debank.com/v1"
        self.headers = {'accept': 'application/json', 'AccessKey': debank_api_key}


    async def get_wallet_tokens(self, wallet_address: str) -> List[dict]:
        """从Debank API获取钱包的token列表"""
        url = f"{self.debank_base_url}/user/token_list"
        params = {
            "id": wallet_address,
            "chain_id": "bera",
            "is_all": "false"
        }
        
        #async with aiohttp.ClientSession() as session:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    raise Exception(f"Failed to fetch tokens: {response.status}")

    async def swap_tokens(self, 
                         wallet_address: str, 
                         target_token: str,
                         excluded_tokens: List[str] = None) -> None:
        """
        将钱包中的token兑换成目标token
        
        Args:
            wallet_address: 钱包地址
            target_token: 目标token地址
            excluded_tokens: 不需要兑换的token地址集合
        """
        if excluded_tokens is None:
            excluded_tokens = []
        
        # 将excluded_tokens转换为小写
        excluded_tokens = [token.lower() for token in excluded_tokens]

        # 获取钱包token列表
        tokens = await self.get_wallet_tokens(wallet_address)
        
        # 获取所有可用的token列表
        available_tokens = await self.client.get_token_list()
        available_token_addresses = {token.address.lower() for token in available_tokens}
        available_token_addresses = [Web3.to_checksum_address(address) for address in available_token_addresses]

        # 遍历每个token进行兑换
        for token in tokens:
            token_address = token.get("id").lower()
            if token_address == "bera":
                continue
            token_address = Web3.to_checksum_address(token_address)
            
            # 跳过不需要兑换的token
            if token_address.lower() in excluded_tokens:
                logger.info(f"Token {token_address} is excluded from swap")
                continue
                
            # 检查token是否在可兑换列表中
            if token_address not in available_token_addresses:
                logger.info(f"Token {token_address} is not available for swap")
                continue

            # 获取token余额
            amount = int(token.get("raw_amount", 0))
            if amount <= 0:
                continue

            try:
                # 检查是否需要授权
                allowance = await self.client.get_token_allowance(
                    from_address=wallet_address,
                    token=token_address
                )
                
                if allowance.allowance == "0":
                    # 授权token
                    await self.client.approve_allowance(token=token_address, amount=str(amount))
                    logger.info(f"Approved {token_address}")

                # 准备swap参数
                swap_params = SwapParams(
                    tokenIn=token_address,
                    amount=amount,
                    tokenOut=target_token,
                    to=wallet_address,
                    slippage=0.02
                )

                # 执行swap
                await self.client.swap(swap_params)
                logger.info(f"Swapped {token_address} to {target_token}")

            except Exception as e:
                logger.error(f"Failed to swap {token_address}: {str(e)}")
                continue

async def main():
    load_dotenv(override=True)
    ooga_booga_api_key = os.getenv("OOGA_BOOGA_API_KEY")
    debank_api_key = os.getenv("DEBANK_API_KEY")
    berachain_rpc_url = os.getenv("BERA_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    wallet_address = os.getenv("WALLET_ADDRESS")
    wallet_address = Account.from_key(private_key).address

    wallet_address = Web3.to_checksum_address(wallet_address)
    logger.info(f"Wallet address: {wallet_address}")

    client = OogaBoogaClient(api_key=ooga_booga_api_key, private_key=private_key, rpc_url=berachain_rpc_url, max_retries=config.max_retries, request_delay=config.request_delay)
    swapper = TokenSwapper(client=client, debank_api_key=debank_api_key)
    await swapper.swap_tokens(wallet_address, config.target_token, config.excluded_tokens)


if __name__ == "__main__":
    asyncio.run(main())