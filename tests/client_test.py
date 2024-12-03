import os
import pytest
from dotenv import load_dotenv

from ooga_booga_python.client import OogaBoogaClient
from ooga_booga_python.models import SwapParams

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OOGA_BOOGA_API_KEY")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

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
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    assert "address" in tokens[0].model_dump()


@pytest.mark.asyncio
async def test_get_token_allowance(client):
    """
    Test fetching token allowance for a specific address and token.
    """
    from_address = "0x31EF7AF5a3497d88bB04943E461B8497AAac6bE3"
    token_address = "0xDFDaeCa74bB2D37204171Ce05fE6bA6AE970D844" # Fake Bera
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
        tokenIn="0x0000000000000000000000000000000000000000",
        amount=1000000000000000000,
        tokenOut="0x0E4aaF1351de4c0264C5c7056Ef3777b41BD8e03",
        to="0x31EF7AF5a3497d88bB04943E461B8497AAac6bE3",
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

