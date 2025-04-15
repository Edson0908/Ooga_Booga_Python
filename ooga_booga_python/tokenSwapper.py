import asyncio
import os
from dotenv import load_dotenv
from typing import List
import aiohttp
from client import OogaBoogaClient
from models import SwapParams, Token
from web3 import Web3
from eth_account import Account
import config
import constants
import utils
import custom_logger
import certifi
import ssl
from datetime import datetime

logger = custom_logger.get_logger(__name__)


class TokenSwapper:
    def __init__(self, client: OogaBoogaClient, debank_api_key: str):
        self.client = client
        self.debank_api_key = debank_api_key
        self.debank_base_url = "https://pro-openapi.debank.com/v1"
        self.headers = {'accept': 'application/json', 'AccessKey': debank_api_key}
        # 创建 SSL 上下文
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.connector = aiohttp.TCPConnector(ssl=self.ssl_context)

    def get_token_balance(self, token_address: str, wallet_address: str, token_decimals: int) -> float:
        """获取钱包的token余额"""
        abi = constants.ERC20_ABI
        token_address = Web3.to_checksum_address(token_address)
        wallet_address = Web3.to_checksum_address(wallet_address)
        w3 = Web3(Web3.HTTPProvider(self.client.rpc_url))
        contract = w3.eth.contract(address=token_address, abi=abi)
        balance = contract.functions.balanceOf(wallet_address).call()
        return round(balance / 10 ** token_decimals, 4)
    
    def get_token_name(self, token_address: str) -> str:
        """获取token名称"""
        abi = constants.ERC20_ABI
        token_address = Web3.to_checksum_address(token_address)
        w3 = Web3(Web3.HTTPProvider(self.client.rpc_url))
        contract = w3.eth.contract(address=token_address, abi=abi)
        return contract.functions.symbol().call()
    
    def get_token_decimals(self, token_address: str) -> int:
        """获取token小数位"""
        abi = constants.ERC20_ABI
        token_address = Web3.to_checksum_address(token_address)
        w3 = Web3(Web3.HTTPProvider(self.client.rpc_url))
        contract = w3.eth.contract(address=token_address, abi=abi)
        return contract.functions.decimals().call()
    
    async def get_wallet_tokens(self, wallet_address: str) -> List[dict]:
        """从Debank API获取钱包的token列表"""
        url = f"{self.debank_base_url}/user/token_list"
        params = {
            "id": wallet_address,
            "chain_id": "bera",
            "is_all": "false"
        }
        
        async with aiohttp.ClientSession(connector=self.connector) as session:
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

        #target_token 信息
        target_token = Web3.to_checksum_address(target_token)
        target_token_name = self.get_token_name(target_token)
        target_token_decimals = self.get_token_decimals(target_token)

        # 遍历每个token进行兑换
        for token in tokens:
            token_address = token.get("id").lower()
            token_decimals = token.get("decimals") 
            token_name = token.get("symbol")
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
            
            token_amount = round(amount / 10 ** token_decimals, 4)

            try:
                # 检查是否需要授权
                allowance = await self.client.get_token_allowance(
                    from_address=wallet_address,
                    token=token_address
                )
                
                if int(allowance.allowance) < amount:
                    # 授权token
                    await self.client.approve_allowance(token=token_address, amount=str(amount))
                    logger.info(f"Approved {token_address}")

                # 准备swap参数
                swap_params = SwapParams(
                    tokenIn=token_address,
                    amount=amount,
                    tokenOut=target_token,
                    to=wallet_address,
                    slippage=config.slippage
                )
                balance0 = self.get_token_balance(target_token, wallet_address, target_token_decimals)
                # 执行swap
                rctp = await self.client.swap(swap_params)
                if rctp.status == 1:
                    balance1 = self.get_token_balance(target_token, wallet_address, target_token_decimals)
                    token_out_amount = round(balance1 - balance0, 4)
                    logger.info(f"Swapped {token_amount} {token_name} to {token_out_amount} {target_token_name}")

                    # save to file
                    data = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "tx_hash": f"0x{rctp['transactionHash'].hex()}",
                        "token_input": token_name,
                        "token_input_amount": token_amount,
                        "token_input_address": token_address,
                        "token_output": target_token_name,
                        "token_output_amount": token_out_amount,
                        "token_output_address": target_token,
                    }
                    utils.save_swap_history(data, wallet_address)
                    logger.info("Save record to file")
                else:
                    logger.error(f"Swap failed: {rctp.status}")
                    continue

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