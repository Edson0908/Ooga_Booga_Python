from typing import List
import aiohttp
import asyncio

from eth_typing import HexStr
from web3 import Web3
from web3.constants import MAX_INT, ADDRESS_ZERO
from web3.types import TxParams

from .custom_logger import get_logger
from .constants import BASE_URL, CHAIN_ID
from .exceptions import APIRequestError, APINotFoundError, APIRateLimitError, APIServerError
from .models import (
    SwapParams,
    Token,
    ApproveResponse,
    AllowanceResponse,
    SwapResponse,
    PriceInfo,
    LiquiditySourcesResponse, SuccessfulSwapResponse,
)

# Logging setup
logger = get_logger(__name__)


class OogaBoogaClient:
    """
    A client for interacting with the Ooga Booga API.

    Attributes:
        api_key (str): API key for authentication.
        max_retries (int): Maximum number of retries for requests.
        request_delay (int): Delay in seconds between retries.
    """
    def __init__(self, api_key: str, private_key: str, rpc_url: str = "https://bartio.rpc.berachain.com/", max_retries: int = 5, request_delay: int = 5):
        if not api_key:
            raise ValueError("API key is required.")
        if not rpc_url:
            raise ValueError("Provider URL is required.")
        if not private_key:
            raise ValueError("Private key is required.")

        self.api_key = api_key
        self.private_key = private_key
        self.rpc_url = rpc_url
        self.max_retries = max_retries
        self.request_delay = request_delay
        self.base_url = BASE_URL
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = self.w3.eth.account.from_key(private_key)
        self.address = self.account.address


    async def _send_request(self, url: str, params: dict = None) -> dict:
        retry = 0
        async with aiohttp.ClientSession() as session:
            while retry < self.max_retries:
                try:
                    async with session.get(url, headers=self.headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            raise APINotFoundError(f"Resource not found at {url}.")
                        elif response.status == 429:
                            raise APIRateLimitError(f"Rate limit exceeded for {url}.")
                        elif 500 <= response.status < 600:
                            raise APIServerError(f"Server error: {response.status} at {url}.")
                        else:
                            retry = await self._handle_errors(response, retry)
                except aiohttp.ClientError as e:
                    logger.error(f"Client error occurred: {e}")
                    retry += 1
                    await asyncio.sleep(self.request_delay)
        raise APIRequestError(f"Failed to fetch data from {url} after {self.max_retries} retries.")


    async def _handle_errors(self, response: aiohttp.ClientResponse, retry: int) -> int:
        """
        Handles HTTP errors and logs them.

        Args:
            response (aiohttp.ClientResponse): The HTTP response object.
            retry (int): Current retry count.

        Returns:
            int: Updated retry count.
        """
        logger.error(
            f"HTTP error {response.status}: {await response.text()} at retry {retry}"
        )
        retry += 1
        await asyncio.sleep(self.request_delay)
        return retry


    async def get_token_list(self) -> List[Token]:
        """
        Fetches a list of all available tokens.

        Returns:
            List[Token]: List of validated Token objects.
        """
        url = f"{self.base_url}/tokens"
        response_data = await self._send_request(url)
        return [Token(**token) for token in response_data]


    async def _prepare_and_send_transaction(self, tx_params: TxParams) -> dict:
        """
        Prepares, signs, and sends a transaction, then waits for the receipt.

        Args:
            tx_params (TxParams): The transaction parameters.

        Returns:
            dict: The transaction receipt.
        """
        logger.info("Signing and sending transaction...")
        signed_tx = self.account.sign_transaction(tx_params)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        rcpt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.info(
            f"Transaction complete: Transaction Hash: 0x{rcpt['transactionHash'].hex()}, Status: {rcpt['status']}")
        return rcpt


    async def _build_transaction(self, to: str, data: str, value: int = 0) -> TxParams:
        """
        Builds a transaction dictionary with common parameters.

        Args:
            to (str): The recipient address.
            data (str): The transaction data.
            value (int, optional): The transaction value. Defaults to 0.

        Returns:
            TxParams: The transaction parameters.
        """
        return {
            "from": self.address,
            "to": to,
            "data": HexStr(data),
            "gas": self.w3.eth.estimate_gas(
                {"from": self.address, "to": to, "data": HexStr(data)}
            ),
            "value": Web3.to_wei(value, "wei"),
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.address),
            "chainId": CHAIN_ID,
        }


    async def swap(self, swap_params: SwapParams):
        url = f"{self.base_url}/swap"
        params = swap_params.model_dump(exclude_none=True)
        print(params)
        response_data = await self._send_request(url, params)
        print(response_data)
        swap_tx = SuccessfulSwapResponse(**response_data).tx

        value = 0 if swap_params.tokenIn != ADDRESS_ZERO else swap_tx.value
        tx_params = await self._build_transaction(
            to=swap_tx.to, data=swap_tx.data, value=value
        )

        logger.info("Submitting swap...")
        await self._prepare_and_send_transaction(tx_params)


    async def approve_allowance(self, token: str, amount: str = MAX_INT) -> None:
        url = f"{self.base_url}/approve"
        params = {"token": token, "amount": amount}
        response_data = await self._send_request(url, params)
        approve_tx = ApproveResponse(**response_data).tx

        tx_params = await self._build_transaction(to=approve_tx.to, data=approve_tx.data)

        logger.info(f"Approving token {token} with amount {amount}...")
        await self._prepare_and_send_transaction(tx_params)


    async def get_token_allowance(self, from_address: str, token: str) -> AllowanceResponse:
        """
        Fetches the allowance of a token for a specific address.

        Args:
            from_address (str): The address to check allowance for.
            token (str): The token address.

        Returns:
            AllowanceResponse: The allowance details.
        """

        if token == ADDRESS_ZERO:
            return AllowanceResponse(allowance=str(MAX_INT))

        url = f"{self.base_url}/approve/allowance"
        params = {"from": from_address, "token": token}
        response_data = await self._send_request(url, params)
        return AllowanceResponse(**response_data)


    async def get_token_prices(self) -> List[PriceInfo]:
        """
        Fetches the current prices of tokens.

        Returns:
            List[PriceInfo]: A list of price information for tokens.
        """
        url = f"{self.base_url}/prices"
        response_data = await self._send_request(url)
        return [PriceInfo(**price) for price in response_data]


    async def get_liquidity_sources(self) -> List[str]:
        """
        Fetches all available liquidity sources.

        Returns:
            List[str]: List of liquidity source names.
        """
        url = f"{self.base_url}/liquidity-sources"
        response_data = await self._send_request(url)
        return LiquiditySourcesResponse(sources=response_data).sources


    async def get_swap_infos(self, swap_params: SwapParams) -> SwapResponse:
        """
        Prepares swap information and routes the swap.

        Args:
            swap_params (SwapParams): Parameters for the swap.

        Returns:
            SwapResponse: The response from the swap endpoint.
        """
        url = f"{self.base_url}/swap/"
        params = swap_params.model_dump(exclude_none=True)
        response_data = await self._send_request(url, params)

        if response_data.get("status") == "NoWay":
            return SwapResponse(response=response_data)
        return SwapResponse(response=response_data)
