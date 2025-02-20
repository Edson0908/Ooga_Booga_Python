import os
import pytest
from dotenv import load_dotenv

from ooga_booga_python.client import OogaBoogaClient
from ooga_booga_python.models import SwapParams

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OOGA_BOOGA_API_KEY")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

TOKEN_IN = "0xFCBD14DC51f0A4d49d5E53C2E0950e0bC26d0Dce" #HONEY MAINNET
TOKEN_OUT = "0x6969696969696969696969696969696969696969" # wBEAR MAINNET
EXECUTOR = "0xa154CCD02848068ceC1c16B3126EBb2BE73553Ed"

# Fixtures
@pytest.fixture
def client():
    if not API_KEY:
        pytest.fail("OOGA_BOOGA_API_KEY is not set in the .env file.")
    if not PRIVATE_KEY:
        pytest.fail("PRIVATE_KEY is not set in the .env file.")
    return OogaBoogaClient(api_key=API_KEY, private_key=PRIVATE_KEY)


# Tests
@pytest.mark.asyncio
async def test_get_token_list(client):
    """
    Test fetching the list of tokens.
    """
    tokens = await client.get_token_list()
    print(tokens)
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert "address" in tokens[0].model_dump()


@pytest.mark.asyncio
async def test_get_token_allowance(client):
    """
    Test fetching token allowance for a specific address and token.
    """
    from_address = TOKEN_IN
    token_address = TOKEN_OUT
    allowance = await client.get_token_allowance(from_address=from_address, token=token_address)
    assert isinstance(allowance.allowance, str), "Allowance is not a string"
    assert allowance.allowance == '0', f"Expected allowance to be '0', got {allowance.allowance}"


@pytest.mark.asyncio
async def test_get_token_prices(client):
    """
    Test fetching token prices.
    """
    prices = await client.get_token_prices()
    assert isinstance(prices, list)
    assert len(prices) > 0
    assert "address" in prices[0].model_dump()
    assert "price" in prices[0].model_dump()


@pytest.mark.asyncio
async def test_get_liquidity_sources(client):
    """
    Test fetching liquidity sources.
    """
    sources = await client.get_liquidity_sources()
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert isinstance(sources[0], str)


@pytest.mark.asyncio
async def test_get_swap_infos(client):
    """
    Test preparing swap information and routing the swap.
    """
    swap_params = SwapParams(
        tokenIn=TOKEN_IN,
        amount=1000000000000000000,
        tokenOut=TOKEN_OUT,
        to=EXECUTOR,
        slippage=0.02,
    )
    swap_info = await client.get_swap_infos(swap_params=swap_params)
    assert swap_info.response.status in ["Success", "Partial", "NoWay"]
    if swap_info.response.status != "NoWay":
        assert isinstance(swap_info.response.price, float)
        assert isinstance(swap_info.response.price, float)
        assert isinstance(swap_info.response.price, float)
        assert swap_info.response.routerParams.swapTokenInfo.inputToken == swap_params.tokenIn
        assert swap_info.response.routerParams.swapTokenInfo.outputToken == swap_params.tokenOut

